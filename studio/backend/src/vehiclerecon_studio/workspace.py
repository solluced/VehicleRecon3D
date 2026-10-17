"""Opaque project registry, leases and adapters over shared core authoring."""
import hashlib
import io
import json
import re
import secrets
import threading
import time
import uuid
import warnings
from pathlib import Path
from PIL import Image
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.authoring.service import AuthoringSession
from vehiclerecon.authoring.versions import create_draft, inspect_version, preview_migration, execute_migration
from vehiclerecon.authoring.readiness import readiness
from vehiclerecon.authoring.contracts import observations, crop_identity, HELPER_ROLES
from vehiclerecon.authoring.imports import import_reference
from vehiclerecon.core.project import Project, RESOURCE_ROOT, read_json
from vehiclerecon.core.revisions import revision
from vehiclerecon.core.locking import ProjectLock
from vehiclerecon.core.manifest import digest_file, digest_data
from vehiclerecon.core.transactions import atomic_write
from vehiclerecon.core.errors import ConflictError, LockError, ReferenceError, SchemaError
from vehiclerecon.reference.panels import inventory
from .events import EventBus
from .retention import Responses


class APIError(Exception):
    def __init__(self,status,code,message):self.status=status;self.code=code;self.message=message


def guard(root, path):
    """Reject aliases/reparse points, including existing parents of new paths."""
    root=Path(root).resolve();path=Path(path)
    if not path.is_relative_to(root):raise APIError(404,'PATH','Unavailable project')
    part=root
    for segment in path.relative_to(root).parts:
        part=part/segment
        if part.exists() or part.is_symlink():
            if part.is_symlink() or getattr(part,'is_junction',lambda:False)():
                raise APIError(403,'PATH','Linked project paths are not allowed')
    resolved=path.resolve()
    if not resolved.is_relative_to(root):raise APIError(403,'PATH','Path escapes allowed root')
    return resolved


class Registry:
    def __init__(self,config):
        self.config=config;self.projects={};self.roots={uuid.uuid4().hex:p for p in config.roots}
        self.lock=threading.RLock();self.sessions={};self.leases={};self.seen={};self.requests=Responses();self.snapshots={};self.analyses={};self.proposals={};self.bus=EventBus();self.decode_slots=threading.BoundedSemaphore(2)
        self.scan()

    def scan(self):
        with self.lock:
            reverse={str(v):k for k,v in self.projects.items()}
            for root in self.roots.values():
                for child in sorted(root.iterdir()):
                    if child.name.startswith('.') or not child.is_dir():continue
                    try:
                        child=guard(root,child)
                        if (child/'project.json').is_file():
                            self.projects[reverse.get(str(child),uuid.uuid4().hex)]=child
                    except APIError:continue

    def root_revision(self,ident):
        if ident not in self.roots:raise APIError(404,'ROOT','Unknown allowed root')
        return digest_data(sorted(p.name for p in self.roots[ident].iterdir() if not p.name.startswith('.')))

    def resolve(self,ident):
        if not re.fullmatch('[0-9a-f]{32}',ident) or ident not in self.projects:raise APIError(404,'PROJECT','Unknown project')
        path=self.projects[ident]
        root=next((r for r in self.roots.values() if path.parent==r),None)
        if root is None:raise APIError(404,'ROOT','Project is outside allowed roots')
        guard(root,path)
        data=read_json(guard(path,path/'project.json'))
        for folder in ('input','generated','validation','.studio','.cache'):guard(path,path/folder)
        for p in [*data.get('references',{}).values(),*data.get('generated',{}).values()]:
            # Project.path adds drive/UNC/backslash/traversal restrictions.
            obj=object.__new__(Project);obj.root=path;obj.path(p)
            guard(path,path/p)
        return path

    def session(self,ident,tab):
        key=(ident,tab)
        if key not in self.sessions:
            self.sessions[key]=self.new_session(ident,tab)
        return self.sessions[key]

    def new_session(self,ident,tab):
        def observer(event):
            self.bus.emit(event['kind'],project_id=ident,revision=event.get('revision'),
                          stale=event.get('stale'),actor_tab=tab.rsplit(':',1)[-1])
        return AuthoringSession(self.resolve(ident),observer=observer,history_limit=100,history_byte_limit=32*1024*1024)

    def analysis(self,ident,expected=None):
        from .analysis import v2_analysis,legacy_analysis
        root=self.resolve(ident)
        with self.lock,ProjectLock(root,'studio-analysis'):
            snap=self.snapshot(ident);rev=snap['revision']
            if expected is not None and rev!=expected:raise ConflictError('Evidence revision changed; reload project')
            cache_key=self.snapshots.get(ident,(rev,))[0]
            cached=self.analyses.get(ident)
            if cached and cached[0]==cache_key:return cached[1]
            if snap['version']==2:result=v2_analysis(Workspace(root))
            else:result=legacy_analysis(Project(root),guard)
            result['revision']=rev
            self.analyses[ident]=(cache_key,result);return result

    def propose(self,ident,tab,body):
        from vehiclerecon.core.project import validate
        from vehiclerecon.authoring.fitting import fit_landmark,place_on_plane
        root=self.resolve(ident)
        with self.lock,ProjectLock(root,'studio-fit-proposal'):
            expected=body.get('expected_revision');lease=self.leases.get(ident)
            if revision(root)!=expected:raise ConflictError('Proposal evidence revision changed')
            if not lease or lease['tab']!=tab or lease['id']!=body.get('lease_id') or lease['expires']<=time.monotonic():raise LockError('Active editor lease required')
            request=body.get('request',{});validate(request,'landmark_fit');w=Workspace(root)
            cage=w.documents.get('cage',{});cal=w.documents.get('calibration',{});name=request['world_entity_id']
            initial=cage.get('landmarks',{}).get(name)
            links={l['observation_id']:l for l in cal.get('correspondences',[]) if l['world_entity_id']==name and l['binding_type']=='landmark'}
            if 'placement' in request:
                p=request['placement'];xyz=place_on_plane(cal,p['view'],p['pixel'],p['normal'],p['offset'])
                result={'status':'PASS','proposed_xyz':xyz,'proposal_only':True,'constraints':[{'normal':p['normal'],'offset':p['offset']}],
                        'rows':[],'observations_used':[],'observations_excluded':[],'conditioning':{'placement':'Explicit plane intersection'},'method':'Calibrated pixel ray / explicit plane'}
            else:
                result=fit_landmark(cal,request['observation_ids'],constraints=request.get('constraints'),excluded_ids=request.get('excluded_ids',()),
                    weights=request.get('weights'),tolerance_px=request.get('tolerance_px',2),initial=initial,links=links)
            result={**result,'revision':expected,'world_entity_id':name,'old_xyz':initial,'proposal_id':uuid.uuid4().hex}
            self.proposals={k:v for k,v in self.proposals.items() if v['expires']>time.monotonic()}
            if len(self.proposals)>=32:self.proposals.pop(next(iter(self.proposals)))
            self.proposals[result['proposal_id']]={'result':result,'ident':ident,'tab':tab,'expires':time.monotonic()+300}
            return result

    def snapshot(self,ident,tab=None):
        root=self.resolve(ident)
        with self.lock,ProjectLock(root,'studio-inspect'):
            current=revision(root);data=read_json(root/'project.json');proofs=set()
            if data.get('schema_version')==2:
                cal_path=data.get('generated',{}).get('calibration')
                if cal_path:proofs.update(read_json(root/cal_path).get('authoring_policy',{}).get('required_proofs',[]))
                for name in ('source','cage'):
                    decision=guard(root,root/f'validation/{name}_review.json')
                    if decision.is_file():proofs.update(read_json(decision).get('proof_hashes',{}))
            proof_hashes={}
            path_project=object.__new__(Project);path_project.root=root
            for relative in proofs:
                path=path_project.path(relative);guard(root,root/relative)
                proof_hashes[relative]=digest_file(path) if path.is_file() else None
            key=digest_data([current,proof_hashes]);cached=self.snapshots.get(ident)
            if cached and cached[0]==key:
                return {**cached[1],**self.presentation(root,ident,tab)}
            info=inspect_version(root)
            if not info['supported']:return {'id':ident,'revision':info['revision'],'version':info['version'],'read_only':True,'issues':info['issues']}
            p=Project(root);v=p.data['schema_version'];cal={};obs=[]
            if v==2:
                w=Workspace(root);cal=w.documents.get('calibration',{});obs=list(observations(cal).values())
            refs=inventory(p)
            for role,ref in refs.items():
                ref['id']=digest_data([role,ref['sha256']])[:32];ref['role']=role;ref.pop('path')
            result={'id':ident,'revision':current,'version':v,'read_only':v!=2,'project':p.data,
                    'references':list(refs.values()),'observations':obs,
                    'views':{name:{'crop_id':{role:crop_identity(role,data.get('crop')) for role in refs}} for name,data in cal.get('views',{}).items()},
                    'roles':p.profile['roles']+p.profile['optional_roles']+list(HELPER_ROLES),
                    'measurements':cal.get('datums',{}).get('measurements',[]),'readiness':readiness(root,workspace=w) if v==2 else readiness(root),
                    **self.presentation(root,ident,tab)}
            self.snapshots[ident]=(key,result)
            return result

    def presentation(self,root,ident,tab):
        history=self.sessions.get((ident,tab));active=self.leases.get(ident)
        editable=bool(active and active['tab']==tab and active['expires']>time.monotonic())
        pref=guard(root,root/'.studio/session.json');preferences={}
        if pref.is_file() and pref.stat().st_size<=2*1024*1024:
            try:preferences=read_json(pref);self.validate_preferences(preferences)
            except SchemaError:preferences={}
        return {'history':{'undo':bool(history and history.undo_stack),'redo':bool(history and history.redo_stack)},'editable':editable,'preferences':preferences}

    def acquire(self,ident,tab,expected):
        root=self.resolve(ident)
        with self.lock,ProjectLock(root,'studio-lease'):
            if revision(root)!=expected:raise ConflictError('Project changed; reload before editing')
            if inspect_version(root)['version']!=2:raise APIError(403,'READ_ONLY','Legacy/future project is read-only')
            lease=self.leases.get(ident)
            if lease and lease['expires']>time.monotonic() and lease['tab']!=tab:raise LockError('Another tab owns the editor lease')
            lease={'id':lease['id'] if lease and lease['tab']==tab else secrets.token_hex(16),'tab':tab,'expires':time.monotonic()+45}
            self.leases[ident]=lease;return {'lease_id':lease['id'],'expires_in':45,'revision':expected}

    def mutate(self,ident,tab,body,key,operation):
        with self.lock:
            if not re.fullmatch('[A-Za-z0-9_-]{16,100}',key or ''):raise APIError(428,'IDEMPOTENCY','Idempotency-Key required')
            fingerprint=digest_data([ident,tab,operation,{k:(hashlib.sha256(v).hexdigest() if isinstance(v,bytes) else v) for k,v in body.items()}]);cached=self.requests.get(key)
            if cached:
                if cached[0]!=fingerprint:raise ConflictError('Idempotency key reused with a different request')
                return cached[1]
            root=self.resolve(ident)
            with ProjectLock(root,'studio-'+operation):
                if inspect_version(root)['version']!=2:raise APIError(403,'READ_ONLY','Legacy project is read-only')
                lease=self.leases.get(ident)
                if not lease or lease['tab']!=tab or lease['id']!=body.get('lease_id') or lease['expires']<=time.monotonic():
                    raise LockError('Editor lease expired or owned by another tab; reopen project')
                expected=body.get('expected_revision')
                if not expected:raise APIError(428,'REVISION','expected_revision required')
                if revision(root)!=expected:
                    self.bus.emit('conflict',project_id=ident,revision=revision(root));raise ConflictError('External revision changed; reload project')
                session=self.session(ident,tab)
                if operation=='transactions':
                    commands=body.get('commands',[])
                    allowed={'AddObservation','MoveObservation','DeleteObservation','SetObservationProperties','AddSplinePoint','MoveSplinePoint','DeleteSplinePoint','SplitSpline','MergeSpline','SetMeasurement','SetProjectMetadata','SetProjectSettings','SetViewerLabel',
                             'AddWorldLandmark','MoveWorldLandmark','DeleteWorldLandmark','BindObservation','UnbindObservation','SetTolerance','SetCoveragePolicy'}
                    if not isinstance(commands,list) or not 1<=len(commands)<=100:raise SchemaError('1..100 commands required')
                    for command in commands:
                        if command.get('type') not in allowed or (command.get('target','observation')!='observation' and command.get('type')!='MoveSplinePoint'):raise SchemaError('Operation unavailable in this authoring workspace')
                        if command.get('type')=='SetProjectSettings' and command.get('section') not in ('validation','authoring_state'):raise SchemaError('Settings section unavailable in manual authoring')
                    result=session.apply(commands,expected_revision=expected)
                elif operation=='apply-fit':
                    proposal=self.proposals.get(body.get('proposal_id'))
                    if not proposal or proposal['ident']!=ident or proposal['tab']!=tab or proposal['expires']<=time.monotonic():raise ConflictError('Proposal expired or belongs to another workspace')
                    fit=proposal['result']
                    if fit['revision']!=expected:raise ConflictError('Proposal was computed from another revision')
                    if fit['proposed_xyz'] is None:raise SchemaError('Underdetermined proposal cannot be applied')
                    result=session.apply([{'type':'MoveWorldLandmark' if fit['old_xyz'] is not None else 'AddWorldLandmark','world_entity_id':fit['world_entity_id'],'point':fit['proposed_xyz']}],expected_revision=expected)
                elif operation in ('source-review','cage-review'):
                    from vehiclerecon.authoring.reviews import subject
                    kind=operation.split('-')[0];w=Workspace(root)
                    if body.get('expected_subject')!=subject(w,kind):raise ConflictError('Inspected review evidence changed')
                    reviewer=body.get('reviewer','');note=body.get('note','')
                    if not isinstance(reviewer,str) or not reviewer.strip() or not isinstance(note,str) or not note.strip():raise SchemaError('Reviewer and a nonempty note are required')
                    result=session.apply([{'type':'SetSourceDisposition' if kind=='source' else 'SetCageReview','decision':body.get('decision'),
                                          'reviewer':reviewer.strip(),'notes':[note.strip()],'expected_subject':body['expected_subject']}],expected_revision=expected)
                elif operation in ('undo','redo'):result=getattr(session,operation)(expected_revision=expected)
                elif operation=='reload':
                    self.sessions[(ident,tab)]=self.new_session(ident,tab);result={'revision':expected}
                elif operation=='preferences':
                    # Typed presentation-only allowlist, never a second geometry store.
                    prefs=body.get('preferences',{})
                    self.validate_preferences(prefs)
                    guard(root,root/'.studio/session.json')
                    atomic_write(root,'.studio/session.json',(json.dumps(prefs)+'\n').encode());result={'revision':expected}
                elif operation=='reference-imports':
                    directory=guard(root,root/'input')
                    size=sum(p.stat().st_size for p in directory.glob('*') if p.is_file())
                    if size+len(body['_raw'])>self.config.workspace_quota:
                        raise APIError(413,'QUOTA','Reference workspace quota exceeded')
                    result=import_reference(session,body['_raw'],reference_id=body.get('reference_id','multiview'),expected_revision=expected)
                else:raise APIError(404,'OPERATION','Unsupported operation')
                self.seen[ident]=result['revision'];lease['expires']=time.monotonic()+45
                snapshot=self.snapshot(ident,tab);result={**result,'snapshot':snapshot}
                self.requests[key]=(fingerprint,result)
                if len(self.requests)>512:self.requests.pop(next(iter(self.requests)))
                for kind in (('session_changed',) if operation in ('preferences','reload') else ('validation_changed','revision_changed')):
                    self.bus.emit(kind,project_id=ident,revision=result['revision'],actor_tab=tab.rsplit(':',1)[-1])
                if operation not in ('preferences','reload'):
                    for kind in ('residuals_changed','source_review_changed','cage_review_changed'):
                        self.bus.emit(kind,project_id=ident,revision=result['revision'],actor_tab=tab.rsplit(':',1)[-1])
                return result

    @staticmethod
    def validate_preferences(prefs):
        from jsonschema import validate
        state={'type':'object','properties':{'visible':{'type':'boolean'},'locked':{'type':'boolean'},'opacity':{'type':'number','minimum':0,'maximum':1},'name':{'type':'string','maxLength':80},'category':{'enum':['image','observations','curves','datums']}},'additionalProperties':False}
        schema={'type':'object','properties':{'active_view':{'enum':['front','side','rear','top']},'reference_id':{'type':'string','maxLength':40},
                'viewport':{'type':'object','properties':{k:{'type':'number','minimum':-1e7,'maximum':1e7} for k in ('x','y','scale')},'additionalProperties':False},
                'viewports':{'type':'object','maxProperties':4,'propertyNames':{'enum':['front','side','rear','top']},'additionalProperties':{'type':'object','required':['x','y','scale'],'properties':{k:{'type':'number','minimum':-1e7,'maximum':1e7} for k in ('x','y','scale')},'additionalProperties':False}},
                'layout':{'enum':['single','two','four','split','all']},
                'secondary_view':{'enum':['front','side','rear','top']},
                **{k:{'type':'boolean'} for k in ('sync_selection','sync_semantic','residual_vectors','residual_labels','heatmap')},
                'layers':{'type':'object','maxProperties':32,'additionalProperties':state},
                'assignments':{'type':'object','maxProperties':20000,'additionalProperties':{'type':'string','maxLength':80}}},'additionalProperties':False}
        try:validate(prefs,schema)
        except Exception as exc:raise SchemaError('Invalid UI preferences: '+getattr(exc,'message','invalid state')) from exc

    def decode_image(self,raw):
        if not self.decode_slots.acquire(blocking=False):raise APIError(429,'DECODE_BUSY','Two image decodes are active; retry after they finish')
        try:return self._decode_image(raw)
        finally:self.decode_slots.release()

    def _decode_image(self,raw):
        if not raw or len(raw)>self.config.max_upload:raise APIError(413,'UPLOAD','Image exceeds encoded size limit')
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            try:
                with Image.open(io.BytesIO(raw)) as image:
                    if image.format not in ('PNG','JPEG'):raise APIError(422,'IMAGE','Only PNG/JPEG reference images are supported')
                    if image.width*image.height>self.config.max_pixels:raise APIError(413,'IMAGE','Decoded image exceeds pixel budget')
                    image.verify()
                with Image.open(io.BytesIO(raw)) as image:
                    if image.getexif().get(274,1)!=1:raise APIError(422,'ORIENTATION','Rotated EXIF images require an upright source; original bytes were not changed')
                    image.load()
            except APIError:raise
            except (Image.DecompressionBombWarning,Image.DecompressionBombError) as exc:
                raise APIError(413,'IMAGE','Decoded image exceeds pixel budget') from exc
            except Exception as exc:raise APIError(422,'IMAGE','Corrupt or unsupported reference image') from exc
