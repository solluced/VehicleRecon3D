import json
import os
import shutil
import subprocess
import sys
import threading
import pytest
from vehiclerecon.core.project import REPOSITORY
from vehiclerecon.core.errors import GateError, LockError, ConflictError
from vehiclerecon.core.pipeline import Status
from vehiclerecon.core.jobs import JobManager, JobResult, Activity
from vehiclerecon.core.events import Events
from vehiclerecon.core.execution import ExecutionControl, current_execution, Cancelled


@pytest.fixture
def root(tmp_path):
    shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',tmp_path,dirs_exist_ok=True)
    return tmp_path


def actions(job, preflight=None):
    def write():
        path=job.workspace/'validation/proof.txt';path.parent.mkdir(exist_ok=True);path.write_text('completed test artifact')
        return ['validation/proof.txt']
    return {'preflight':preflight or write,'references':write}


def test_native_stage_vocabulary_and_optional_isolated_observers():
    assert {s.value for s in Status}=={'PASS','FAIL','SKIP','BLOCKED'}
    events=Events();assert events.emit('stage_started',stage='test')['kind']=='stage_started'
    def bad(event):raise ValueError('observer failed')
    seen=[];events=Events((bad,seen.append));events.emit('validation_changed')
    assert seen and events.errors


def test_queued_cancel_before_execution_and_repeat(root):
    m=JobManager();job=m.submit(root,until='references',use_cache=False)
    assert m.cancel(job.job_id)['result']=='CANCELLED'
    assert job.result==JobResult.CANCELLED and job.activity==Activity.FINISHED and not job.promotable
    assert m.cancel(job.job_id)['already_finalized']
    m.run(job.job_id,actions=actions(job))
    assert not job.stages and job.workspace is None and m.current(root) is None


def test_cancel_before_first_stage(root):
    holder={}
    def observer(event):
        if event['kind']=='job_started':m.cancel(event['job_id'])
    m=JobManager(observers=(observer,));job=m.submit(root,until='references',use_cache=False)
    m.run(job.job_id,actions=actions(job))
    assert job.result==JobResult.CANCELLED and not job.stages and not job.interrupted
    assert m.current(root) is None


def test_between_stages_preserves_completed_results(root):
    def observer(event):
        if event['kind']=='stage_finished' and event['stage']=='preflight':m.cancel(job.job_id)
    m=JobManager(observers=(observer,));job=m.submit(root,until='references',use_cache=False)
    m.run(job.job_id,actions=actions(job))
    assert job.result==JobResult.CANCELLED
    assert [(s['stage'],s['result']) for s in job.stages]==[('preflight','PASS')]
    assert not job.interrupted and not job.promotable
    assert not any(s['stage']=='references' and s['result']=='PASS' for s in job.stages)


def test_running_non_blender_cancellation_waits_for_worker_return(root):
    entered=threading.Event();release=threading.Event();errors=[]
    m=JobManager();job=m.submit(root,until='references',use_cache=False)
    def action():
        entered.set()
        if not release.wait(15):raise RuntimeError('test handshake timed out')
        return []
    def run():
        try:m.run(job.job_id,actions=actions(job,action))
        except BaseException as exc:errors.append(exc)
    thread=threading.Thread(target=run);thread.start()
    try:
        assert entered.wait(15)
        assert m.cancel(job.job_id)['accepted']
        assert m.cancel(job.job_id)['repeated']
        assert job.result is None and job.activity==Activity.CANCELLING
    finally:release.set();thread.join(15)
    assert not thread.is_alive() and not errors
    assert job.result==JobResult.CANCELLED and job.interrupted[0]['stage']=='preflight'
    assert all(s['result']!='FAIL' for s in job.stages)


@pytest.mark.parametrize('fail',[False,True])
def test_final_result_is_not_rewritten_by_late_cancel(root,fail):
    m=JobManager();job=m.submit(root,until='preflight',use_cache=False)
    def failure():raise GateError('real computation failure')
    m.run(job.job_id,actions=actions(job,failure if fail else None))
    expected=JobResult.FAILED if fail else JobResult.SUCCEEDED
    assert job.result==expected
    assert m.cancel(job.job_id)['already_finalized'] and job.result==expected
    if not fail:
        assert m.current(root)['job_id']==job.job_id
    else:assert m.current(root) is None


def test_real_failure_wins_even_when_cancellation_is_requested(root):
    m=JobManager();job=m.submit(root,until='references',use_cache=False)
    def failure():
        m.cancel(job.job_id)
        raise GateError('independent actual stage failure')
    m.run(job.job_id,actions=actions(job,failure))
    assert job.result==JobResult.FAILED
    assert job.stages[0]['result']=='FAIL' and not job.promotable
    report=json.loads((job.workspace/'validation/pipeline_report.json').read_text())
    assert report['status']=='FAIL'


def test_completed_stale_inputs_cannot_be_promoted(root):
    m=JobManager();job=m.submit(root,until='preflight',use_cache=False)
    def external_edit():
        path=root/'project.json';path.write_bytes(path.read_bytes()+b'\n')
        return []
    m.run(job.job_id,actions=actions(job,external_edit))
    assert job.result==JobResult.SUCCEEDED and job.freshness=='stale' and not job.promotable
    assert m.current(root) is None
    with pytest.raises(ConflictError):m.promote(job.job_id)


def test_promotion_rechecks_inputs_after_completion_event(root):
    def observer(event):
        if event['kind']=='job_finished':
            path=root/'project.json';path.write_bytes(path.read_bytes()+b'\n')
    m=JobManager(observers=(observer,));job=m.submit(root,until='preflight',use_cache=False)
    m.run(job.job_id,actions=actions(job))
    assert job.result==JobResult.SUCCEEDED and job.freshness=='stale' and not job.promotable
    assert m.current(root) is None


def test_changed_queued_inputs_and_corrupt_artifact(root):
    m=JobManager();job=m.submit(root,until='preflight',use_cache=False)
    path=root/'project.json';original=path.read_bytes();path.write_bytes(original+b'\n')
    m.run(job.job_id,actions=actions(job))
    assert job.result==JobResult.BLOCKED and job.freshness=='stale' and not job.stages
    fresh=m.submit(root,until='preflight',use_cache=False);m.run(fresh.job_id,actions=actions(fresh))
    assert m.current(root)['job_id']==fresh.job_id
    (fresh.workspace/'validation/proof.txt').write_text('corrupt')
    assert m.current(root) is None
    with pytest.raises(ConflictError):m.promote(fresh.job_id)


def test_dispatcher_serializes_requests(root):
    m=JobManager();first=m.submit(root,until='preflight',use_cache=False);second=m.submit(root,until='preflight',use_cache=False)
    def during():
        with pytest.raises(LockError):m.run(second.job_id,actions=actions(second))
        return []
    m.run(first.job_id,actions=actions(first,during))
    assert second.activity==Activity.QUEUED
    m.cancel(second.job_id)
    assert m.run_next() is None


def test_owned_process_tree_is_fenced_before_cancelled_result(root):
    events=[]
    def observer(event):
        events.append(event)
        if event['kind']=='job_log' and 'CHILD_READY' in event['text']:m.cancel(job.job_id)
    m=JobManager(observers=(observer,));job=m.submit(root,until='preflight',use_cache=False)
    def action():
        code="import subprocess,sys; child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(120)']); print('CHILD_READY',child.pid,flush=True); child.wait()"
        current_execution().run_process([sys.executable,'-u','-c',code],cwd=REPOSITORY,timeout=20)
        return []
    m.run(job.job_id,actions=actions(job,action))
    assert job.result==JobResult.CANCELLED and not job.control.workers
    assert job.control.worker_history and all(x['cleaned'] for x in job.control.worker_history)
    assert any(e['kind']=='worker_finished' and e['fenced'] for e in events)
    assert not any(s['result']=='FAIL' for s in job.stages)
    assert m.current(root) is None
    # The direct worker has exited; Windows job close/POSIX group kill fences descendants too.
    pids=[e['pid'] for e in events if e['kind']=='worker_started']
    assert pids
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        child_pid=int(next(e['text'].split('CHILD_READY',1)[1].strip() for e in events if e['kind']=='job_log' and 'CHILD_READY' in e['text']))
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];api.OpenProcess.restype=wintypes.HANDLE
        api.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];api.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=api.OpenProcess(0x100000,False,child_pid)
        if handle:
            try:assert api.WaitForSingleObject(handle,5000)==0
            finally:api.CloseHandle(handle)


@pytest.mark.blender
def test_cancel_during_real_blender_subprocess(root):
    from vehiclerecon.blender.runner import discover
    def observer(event):
        if event['kind']=='job_log' and 'BLENDER_CANCEL_READY' in event['text']:m.cancel(job.job_id)
    m=JobManager(observers=(observer,));job=m.submit(root,until='preflight',use_cache=False)
    def action():
        expression="import time; print('BLENDER_CANCEL_READY',flush=True); time.sleep(120)"
        current_execution().run_process([str(discover()),'--factory-startup','--background','--python-exit-code','1','--python-expr',expression],cwd=REPOSITORY,timeout=30)
        return []
    m.run(job.job_id,actions=actions(job,action))
    assert job.result==JobResult.CANCELLED and not job.promotable
    assert not job.control.workers and job.control.worker_history[-1]['cleaned']
    assert all(s['result']!='FAIL' for s in job.stages)


def test_genuine_worker_exit_wins_over_late_cancellation(root):
    def observer(event):
        if event['kind']=='worker_finished':m.cancel(job.job_id)
    m=JobManager(observers=(observer,));job=m.submit(root,until='preflight',use_cache=False)
    def action():
        result=current_execution().run_process([sys.executable,'-c','raise SystemExit(7)'],timeout=15)
        if result.returncode:raise GateError('real worker failure: 7')
        return []
    m.run(job.job_id,actions=actions(job,action))
    assert job.result==JobResult.FAILED and job.stages[0]['result']=='FAIL'


@pytest.mark.skipif(os.name!='nt',reason='Windows suspended-child fencing failure path')
def test_fencing_failure_kills_suspended_worker(root,monkeypatch):
    import vehiclerecon.core.execution as execution
    def fail(process):raise OSError('injected assignment failure')
    monkeypatch.setattr(execution,'_WindowsFence',fail)
    m=JobManager();job=m.submit(root,until='preflight',use_cache=False)
    def action():
        current_execution().run_process([sys.executable,'-c',"raise RuntimeError('must never run unfenced')"],timeout=15)
        return []
    m.run(job.job_id,actions=actions(job,action))
    assert job.result==JobResult.FAILED and not job.control.workers
    assert job.control.worker_history[-1]['cleaned'] and not job.promotable


def test_review_proofs_are_pinned_copied_and_rechecked(root):
    from vehiclerecon.authoring.service import AuthoringSession
    from vehiclerecon.authoring.workspace import Workspace
    from vehiclerecon.authoring.reviews import subject, require_acceptance
    from vehiclerecon.core.revisions import revision
    proof=root/'validation/inspected.png'
    proof.write_bytes((root/'input/reference.png').read_bytes())
    session=AuthoringSession(root)
    policy=Workspace(root).documents['calibration']['authoring_policy']
    policy['required_proofs']=['validation/inspected.png']
    session.apply([{'type':'SetCoveragePolicy','policy':policy}],expected_revision=session.revision)
    for kind,command in [('source','SetSourceDisposition'),('cage','SetCageReview')]:
        session.apply([{'type':command,'decision':'ACCEPTED','reviewer':'Test reviewer',
                        'notes':['Inspected analytical proof.'],'expected_subject':subject(Workspace(root),kind)}],
                      expected_revision=session.revision)
    m=JobManager();job=m.submit(root,until='preflight',use_cache=False)
    before=revision(root)
    def action():
        require_acceptance(Workspace(job.workspace))
        assert (job.workspace/'validation/inspected.png').read_bytes()==proof.read_bytes()
        proof.write_bytes(proof.read_bytes()+b'external replacement')
        return []
    m.run(job.job_id,actions=actions(job,action))
    assert revision(root)==before  # A derived proof is not canonical geometry.
    assert job.result==JobResult.SUCCEEDED and job.freshness=='stale' and not job.promotable
    assert m.current(root) is None
