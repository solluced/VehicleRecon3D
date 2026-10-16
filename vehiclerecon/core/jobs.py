"""Run-scoped managed jobs: pinned inputs, distinct outcomes, guarded promotion."""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import re
import threading
import uuid
from .errors import ReconError, ConflictError, LockError
from .events import Events
from .execution import CancellationToken, ExecutionControl, Cancelled, execution_context
from .locking import ProjectLock
from .manifest import digest_file
from .project import Project, read_json
from .revisions import revision, snapshot, safe_path
from .transactions import atomic_write, digest


class JobResult(str, Enum):
    SUCCEEDED='SUCCEEDED'
    FAILED='FAILED'
    BLOCKED='BLOCKED'
    CANCELLED='CANCELLED'


class Activity(str, Enum):
    QUEUED='QUEUED'
    RUNNING='RUNNING'
    CANCELLING='CANCELLING'
    FINISHED='FINISHED'


@dataclass
class ManagedJob:
    job_id: str
    project: Path
    pinned_revision: str
    input_hashes: dict
    implementation: str
    until: str | None = None
    use_cache: bool = True
    activity: Activity = Activity.QUEUED
    result: JobResult | None = None
    freshness: str = 'current'
    promotable: bool = False
    workspace: Path | None = None
    artifacts: dict = field(default_factory=dict)
    logs: list = field(default_factory=list)
    stages: list = field(default_factory=list)
    interrupted: list = field(default_factory=list)
    error: str | None = None
    token: CancellationToken = field(default_factory=CancellationToken)
    control: ExecutionControl | None = None
    events: Events | None = None


class JobManager:
    def __init__(self, *, observers=()):
        self.jobs={};self.observers=tuple(observers);self._state=threading.RLock();self._dispatcher=threading.Lock()

    def submit(self, root, *, until=None, use_cache=True, expected_revision=None):
        from .pipeline import STAGES
        from .cache import implementation_hash
        if until is not None and until not in {s.id for s in STAGES}:raise ReconError('Unknown job stage')
        root=Path(root).resolve()
        with ProjectLock(root,'job-submit'):
            Project(root);current=revision(root)
            if expected_revision is not None and expected_revision!=current:raise ConflictError('CONFLICT: job inputs changed')
            job=ManagedJob(uuid.uuid4().hex,root,current,{p:digest(raw) for p,raw in self._inputs(root).items()},
                           implementation_hash(),until,use_cache)
            def observe(event):
                if event['kind']=='job_log':
                    with self._state:
                        job.logs.append({'channel':event['channel'],'text':event['text']})
                        if len(job.logs)>10000:del job.logs[:len(job.logs)-10000]
            job.events=Events((observe,*self.observers));job.control=ExecutionControl(token=job.token,events=job.events,job_id=job.job_id)
            with self._state:self.jobs[job.job_id]=job
            self._persist(job);job.events.emit('job_queued',job_id=job.job_id,revision=current)
            return job

    def _persist(self, job):
        record={'schema_version':1,'job_id':job.job_id,'pinned_revision':job.pinned_revision,
                'input_hashes':job.input_hashes,'implementation':job.implementation,'until':job.until,
                'activity':job.activity.value,'result':job.result.value if job.result else None,
                'freshness':job.freshness,'promotable':job.promotable,'artifacts':job.artifacts,
                'logs':job.logs,'stages':job.stages,'interrupted':job.interrupted,'error':job.error,
                'workers':job.control.worker_history if job.control else []}
        atomic_write(job.project,'.cache/jobs/'+job.job_id+'/job.json',(json.dumps(record,indent=2)+'\n').encode('utf-8'))

    def cancel(self, job_id):
        with self._state:
            job=self.jobs[job_id]
            if job.result is not None:
                return {'accepted':False,'already_finalized':True,'result':job.result.value}
            repeated=job.token.requested;job.token.request()
            if job.activity==Activity.QUEUED:
                job.activity=Activity.FINISHED;job.result=JobResult.CANCELLED;job.promotable=False
                self._persist(job);job.events.emit('job_cancelled',job_id=job.job_id,result=job.result.value)
            else:
                job.activity=Activity.CANCELLING;self._persist(job)
                job.events.emit('job_cancelling',job_id=job.job_id)
            return {'accepted':True,'repeated':repeated,'result':job.result.value if job.result else None}

    def _inputs(self, root):
        """Pin derived proof dependencies separately from canonical authoring revision."""
        raw=snapshot(root)
        project=json.loads(raw['project.json'].decode('utf-8-sig'))
        if project.get('schema_version')==2:
            calibration=raw.get(project.get('generated',{}).get('calibration'))
            paths=set()
            if calibration:
                paths.update(json.loads(calibration.decode('utf-8-sig')).get('authoring_policy',{}).get('required_proofs',[]))
            for name in ('source','cage'):
                review=raw.get('validation/'+name+'_review.json')
                if review:paths.update(json.loads(review.decode('utf-8-sig')).get('proof_hashes',{}))
            for relative in paths:
                path=safe_path(root,relative)
                raw[relative]=path.read_bytes() if path.is_file() else None
        return raw

    def _stage_inputs(self, job):
        raw=self._inputs(job.project)
        if revision(job.project)!=job.pinned_revision:raise ConflictError('Pinned job inputs changed before execution')
        workspace=safe_path(job.project,'.cache/jobs/'+job.job_id+'/workspace')
        workspace.mkdir(parents=True,exist_ok=False);job.workspace=workspace
        for relative,data in raw.items():
            if data is not None:atomic_write(workspace,relative,data)
        if {p:digest(v) for p,v in self._inputs(workspace).items()}!=job.input_hashes:
            raise ConflictError('Pinned snapshot copy differs from submitted inputs')
        if job.use_cache:self._seed_cache(job)

    def _seed_cache(self, job):
        from .pipeline import STAGES
        sources=[job.project]
        pointer=safe_path(job.project,'.cache/jobs/current.json')
        if pointer.is_file():
            data=read_json(pointer);ident=data.get('job_id','')
            if re.fullmatch('[0-9a-f]{32}',ident):sources.insert(0,safe_path(job.project,'.cache/jobs/'+ident+'/workspace'))
        for source in reversed(sources):
            for stage in [s.id for s in STAGES]+['presentation_assets']:
                path=safe_path(source,'.cache/'+stage+'.json')
                if not path.is_file():continue
                try:
                    entry=read_json(path)
                    if entry.get('status')!='PASS':continue
                    items=entry['outputs']
                    if not all(digest_file(safe_path(source,i['path']))==i['sha256'] for i in items):continue
                    if any(i['path'] in job.input_hashes and i['sha256']!=job.input_hashes[i['path']] for i in items):continue
                    for item in items:atomic_write(job.workspace,item['path'],safe_path(source,item['path']).read_bytes())
                    atomic_write(job.workspace,'.cache/'+stage+'.json',path.read_bytes())
                except (OSError,KeyError,ValueError,ReconError):continue

    def refresh(self, job):
        from .cache import implementation_hash
        job.freshness=('current' if revision(job.project)==job.pinned_revision and implementation_hash()==job.implementation
                       and {p:digest(v) for p,v in self._inputs(job.project).items()}==job.input_hashes else 'stale')
        valid=all(safe_path(job.workspace,p).is_file() and digest_file(safe_path(job.workspace,p))==sha
                  for p,sha in job.artifacts.items()) if job.workspace else False
        job.promotable=(job.result==JobResult.SUCCEEDED and job.freshness=='current' and valid
                        and not job.control.workers)
        return job

    def promote(self, job_id):
        job=self.jobs[job_id]
        with ProjectLock(job.project,'job-promotion',job.pinned_revision):
            self.refresh(job)
            if not job.promotable:raise ConflictError('Job is cancelled, incomplete, failed, blocked, stale or corrupt; NOT PROMOTABLE')
            pointer={'schema_version':1,'job_id':job.job_id,'input_revision':job.pinned_revision,
                     'implementation':job.implementation,'input_hashes':job.input_hashes,'artifacts':job.artifacts}
            atomic_write(job.project,'.cache/jobs/current.json',(json.dumps(pointer,indent=2)+'\n').encode('utf-8'))
            self._persist(job)
            return pointer

    def current(self, root):
        from .cache import implementation_hash
        root=Path(root).resolve()
        with ProjectLock(root,'current-job-read'):
            path=safe_path(root,'.cache/jobs/current.json')
            if not path.is_file():return None
            pointer=read_json(path);ident=pointer.get('job_id','')
            if not re.fullmatch('[0-9a-f]{32}',ident):return None
            if pointer['input_revision']!=revision(root) or pointer['implementation']!=implementation_hash():return None
            if pointer.get('input_hashes')!={p:digest(v) for p,v in self._inputs(root).items()}:return None
            workspace=safe_path(root,'.cache/jobs/'+ident+'/workspace')
            if not all(safe_path(workspace,p).is_file() and digest_file(safe_path(workspace,p))==sha for p,sha in pointer['artifacts'].items()):return None
            return pointer

    def run(self, job_id, *, actions=None):
        from .pipeline import Pipeline,Status
        job=self.jobs[job_id]
        if not self._dispatcher.acquire(blocking=False):raise LockError('Another backend job is running; request stays queued')
        pipeline=None
        try:
            with self._state:
                if job.result is not None:return job
            with ProjectLock(job.project,'managed-job',job.pinned_revision):
                try:
                    with self._state:
                        if job.result is not None:return job
                        job.activity=Activity.RUNNING
                    job.token.check()
                    self._stage_inputs(job)
                    job.token.check();self._persist(job)
                    job.events.emit('job_started',job_id=job.job_id,revision=job.pinned_revision)
                    with execution_context(job.control):
                        pipeline=Pipeline(Project(job.workspace),use_cache=job.use_cache)
                        code=pipeline.run(actions=actions,until=job.until)
                    real_failure=any(r.status==Status.FAIL for r in pipeline.results)
                    if real_failure:job.result=JobResult.FAILED
                    elif job.token.requested:job.result=JobResult.CANCELLED
                    elif code:job.result=JobResult.BLOCKED
                    else:job.result=JobResult.SUCCEEDED
                except Cancelled:
                    job.result=(JobResult.FAILED if pipeline and any(r.status==Status.FAIL for r in pipeline.results) else JobResult.CANCELLED)
                except ConflictError as exc:job.result=JobResult.BLOCKED;job.error=str(exc)
                except Exception as exc:job.result=JobResult.FAILED;job.error=str(exc)
                if pipeline:
                    job.stages=[{'stage':r.stage,'result':r.status.value,'message':r.message} for r in pipeline.results]
                    job.interrupted=getattr(pipeline,'interrupted',[])
                    for result in pipeline.results:
                        if result.status in (Status.PASS,Status.SKIP):
                            for relative in result.outputs:
                                path=safe_path(job.workspace,relative)
                                if path.is_file():job.artifacts[relative]=digest_file(path)
                job.activity=Activity.FINISHED
                self.refresh(job);self._persist(job)
                if job.result==JobResult.CANCELLED:job.events.emit('job_cancelled',job_id=job.job_id,result=job.result.value)
                job.events.emit('job_finished',job_id=job.job_id,result=job.result.value,freshness=job.freshness,promotable=job.promotable)
                if job.promotable:
                    try:self.promote(job.job_id)
                    except ConflictError as exc:
                        job.error=str(exc);self._persist(job)
                return job
        finally:self._dispatcher.release()

    def run_next(self, *, actions=None):
        for job in self.jobs.values():
            if job.activity==Activity.QUEUED:return self.run(job.job_id,actions=actions)
        return None
