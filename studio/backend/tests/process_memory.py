"""Read RSS of the test-owned backend PID returned by the trusted harness."""
import ctypes
import os
from pathlib import Path
import sys

pid=int(sys.argv[1])
if os.name=='nt':
    from ctypes import wintypes as w
    class Counters(ctypes.Structure):
        _fields_=[('cb',w.DWORD),('faults',w.DWORD)]+[(name,ctypes.c_size_t) for name in (
            'peak_rss','rss','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);api=ctypes.WinDLL('psapi',use_last_error=True)
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
    kernel.CloseHandle.argtypes=[w.HANDLE]
    api.GetProcessMemoryInfo.argtypes=[w.HANDLE,ctypes.POINTER(Counters),w.DWORD]
    handle=kernel.OpenProcess(0x410,False,pid)
    if not handle:raise OSError('Cannot inspect test-owned backend')
    try:
        result=Counters();result.cb=ctypes.sizeof(result)
        if not api.GetProcessMemoryInfo(handle,ctypes.byref(result),result.cb):raise OSError('Memory query failed')
        print(result.peak_rss if '--peak' in sys.argv else result.rss)
    finally:kernel.CloseHandle(handle)
else:
    status=Path(f'/proc/{pid}/status').read_text()
    key='VmHWM:' if '--peak' in sys.argv else 'VmRSS:'
    print(int(next(line.split()[1] for line in status.splitlines() if line.startswith(key)))*1024)
