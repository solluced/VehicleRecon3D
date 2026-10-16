"""Managed cancellation and owned process trees, independent of any transport."""
from contextvars import ContextVar
from contextlib import contextmanager
import os
import queue
import signal
import subprocess
import threading
import time
from .errors import ReconError
from .events import Events

_current = ContextVar('vehiclerecon_execution',default=None)


class Cancelled(Exception):
    """Interrupted execution, deliberately not a native stage failure."""


class CancellationToken:
    def __init__(self):self._requested = threading.Event()
    def request(self):self._requested.set()
    @property
    def requested(self):return self._requested.is_set()
    def check(self):
        if self.requested:raise Cancelled('Managed cancellation requested')


def current_execution():return _current.get()


def check_cancelled():
    control = current_execution()
    if control:control.token.check()


@contextmanager
def execution_context(control):
    marker = _current.set(control)
    try:yield control
    finally:_current.reset(marker)


class _WindowsFence:
    """Assign a suspended child before any user code can create descendants."""
    def __init__(self, process):
        import ctypes as c
        from ctypes import wintypes as w
        self.c = c;self.w = w;self.handle = None
        self.api = c.WinDLL('kernel32',use_last_error=True)
        class Basic(c.Structure):
            _fields_ = [('process_time',c.c_longlong),('job_time',c.c_longlong),('flags',w.DWORD),
                        ('min_ws',c.c_size_t),('max_ws',c.c_size_t),('active_limit',w.DWORD),
                        ('affinity',c.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
        class IO(c.Structure):
            _fields_ = [(name,c.c_ulonglong) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
        class Extended(c.Structure):
            _fields_ = [('basic',Basic),('io',IO),('process_memory',c.c_size_t),('job_memory',c.c_size_t),
                        ('peak_process',c.c_size_t),('peak_job',c.c_size_t)]
        self.api.CreateJobObjectW.argtypes = [c.c_void_p,w.LPCWSTR];self.api.CreateJobObjectW.restype = w.HANDLE
        self.api.SetInformationJobObject.argtypes = [w.HANDLE,c.c_int,c.c_void_p,w.DWORD]
        self.api.AssignProcessToJobObject.argtypes = [w.HANDLE,w.HANDLE]
        self.api.TerminateJobObject.argtypes = [w.HANDLE,w.UINT]
        self.api.CloseHandle.argtypes = [w.HANDLE]
        handle = self.api.CreateJobObjectW(None,None)
        if not handle:raise OSError(c.get_last_error(),'CreateJobObjectW failed')
        self.handle = handle
        try:
            info = Extended();info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not self.api.SetInformationJobObject(handle,9,c.byref(info),c.sizeof(info)):
                raise OSError(c.get_last_error(),'SetInformationJobObject failed')
            if not self.api.AssignProcessToJobObject(handle,w.HANDLE(int(process._handle))):
                raise OSError(c.get_last_error(),'Cannot safely fence owned worker')
        except BaseException:
            self.close();raise

    def resume(self, pid):
        c,w,api = self.c,self.w,self.api
        class ThreadEntry(c.Structure):
            _fields_ = [('size',w.DWORD),('usage',w.DWORD),('thread_id',w.DWORD),('process_id',w.DWORD),
                        ('base_priority',w.LONG),('delta_priority',w.LONG),('flags',w.DWORD)]
        api.CreateToolhelp32Snapshot.argtypes = [w.DWORD,w.DWORD];api.CreateToolhelp32Snapshot.restype = w.HANDLE
        api.Thread32First.argtypes = [w.HANDLE,c.POINTER(ThreadEntry)]
        api.Thread32Next.argtypes = [w.HANDLE,c.POINTER(ThreadEntry)]
        api.OpenThread.argtypes = [w.DWORD,w.BOOL,w.DWORD];api.OpenThread.restype = w.HANDLE
        api.ResumeThread.argtypes = [w.HANDLE];api.ResumeThread.restype = w.DWORD
        handle = api.CreateToolhelp32Snapshot(4,0)
        if handle == c.c_void_p(-1).value:raise OSError(c.get_last_error(),'Thread snapshot failed')
        try:
            entry = ThreadEntry();entry.size = c.sizeof(entry);ok = api.Thread32First(handle,c.byref(entry))
            while ok:
                if entry.process_id == pid:
                    thread = api.OpenThread(2,False,entry.thread_id)
                    if not thread:raise OSError(c.get_last_error(),'Cannot open suspended worker thread')
                    try:
                        if api.ResumeThread(thread)==0xffffffff:raise OSError(c.get_last_error(),'Cannot resume worker')
                    finally:api.CloseHandle(thread)
                    return
                ok = api.Thread32Next(handle,c.byref(entry))
            raise OSError('Suspended worker thread not found')
        finally:api.CloseHandle(handle)

    def close(self):
        if self.handle:
            try:
                if not self.api.TerminateJobObject(self.handle,1):
                    raise OSError(self.c.get_last_error(),'Owned worker termination failed')
            finally:
                self.api.CloseHandle(self.handle);self.handle = None


class ExecutionControl:
    def __init__(self, *, token=None, events=None, job_id=None):
        self.token = token or CancellationToken();self.events = events or Events();self.job_id = job_id
        self.stage = None;self.workers = {};self.worker_history = []

    def emit(self, kind, **data):
        return self.events.emit(kind,job_id=self.job_id,stage=self.stage,**data)

    def run_process(self, command, *, cwd=None, timeout=None):
        """Trusted argument vector only; wait for process cleanup before cancellation."""
        self.token.check()
        options = {'start_new_session':True} if os.name!='nt' else {
            'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW | 0x4}
        process = subprocess.Popen(command,cwd=cwd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',**options)
        fence = None;threads = [];messages = queue.Queue(maxsize=128);outputs = {'stdout':[],'stderr':[]}
        sizes = {'stdout':0,'stderr':0};cancelled = False;started = time.monotonic()
        info = {'pid':process.pid,'fence':'windows_job' if os.name=='nt' else 'posix_session','cleaned':False}
        self.workers[process.pid] = info
        def read(channel, stream):
            try:
                while True:
                    line = stream.readline(65536)
                    if not line:break
                    messages.put((channel,line))
            finally:stream.close()
        def drain():
            while True:
                try:channel,line = messages.get_nowait()
                except queue.Empty:break
                if sizes[channel]<8*1024*1024:
                    outputs[channel].append(line);sizes[channel] += len(line)
                self.emit('job_log',channel=channel,text=line)
        def stop():
            nonlocal fence
            if fence:
                fence.close();fence = None
            elif os.name!='nt':
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
            elif process.poll() is None:
                # An assignment failure leaves the only child still suspended.
                process.kill()
        try:
            if os.name=='nt':fence = _WindowsFence(process)
            for channel in ('stdout','stderr'):
                thread = threading.Thread(target=read,args=(channel,getattr(process,channel)),daemon=True)
                thread.start();threads.append(thread)
            self.emit('worker_started',pid=process.pid,fence=info['fence'])
            if fence:fence.resume(process.pid)
            while True:
                drain()
                code = process.poll()
                # A naturally observed nonzero exit precedes a later cancel.
                if code is not None:break
                if self.token.requested:
                    cancelled = True;stop();break
                if timeout is not None and time.monotonic()-started > timeout:
                    raise ReconError('Owned worker timeout')
                try:process.wait(timeout=.02)
                except subprocess.TimeoutExpired:pass
            process.wait(timeout=15)
            stop()  # Fence/terminate any owned descendants even after parent exit.
            while any(t.is_alive() for t in threads):
                drain()
                for thread in threads:thread.join(timeout=.02)
            drain()
            if cancelled or (process.returncode==0 and self.token.requested):
                raise Cancelled('Owned worker cancelled after termination/fencing')
            return subprocess.CompletedProcess(command,process.returncode,''.join(outputs['stdout']),''.join(outputs['stderr']))
        finally:
            stop()
            process.wait(timeout=15)
            while any(t.is_alive() for t in threads):
                drain()
                for thread in threads:thread.join(timeout=.02)
            drain()
            for stream in (process.stdout,process.stderr):
                if not stream.closed:stream.close()
            info['cleaned'] = True;self.worker_history.append(info);self.workers.pop(process.pid,None)
            self.emit('worker_finished',pid=process.pid,fenced=True,returncode=process.returncode)
