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
from vehiclerecon.authoring.contracts import observations, crop_identity
from vehiclerecon.authoring.imports import import_reference
from vehiclerecon.core.project import Project, RESOURCE_ROOT, read_json
from vehiclerecon.core.revisions import revision
from vehiclerecon.core.locking import ProjectLock
from vehiclerecon.core.manifest import digest_file, digest_data
from vehiclerecon.core.transactions import atomic_write
from vehiclerecon.core.errors import ConflictError, LockError, ReferenceError, SchemaError
from vehiclerecon.reference.panels import inventory
from .events import EventBus


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
        self.lock=threading.RLock();self.sessions={};self.leases={};self.seen={};self.requests={};self.bus=EventBus()
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
            self.sessions[key]=AuthoringSession(self.resolve(ident))
        return self.sessions[key]

    def snapshot(self,ident,tab=None):
        root=self.resolve(ident)
        with ProjectLock(root,'studio-inspect'):
            info=inspect_version(root)
            if not info['supported']:return {'id':ident,'revision':info['revision'],'version':info['version'],'read_only':True,'issues':info['issues']}
            p=Project(root);v=p.data['schema_version'];cal={};obs=[]
            if v==2:
                w=Workspace(root);cal=w.documents.get('calibration',{});obs=list(observations(cal).values())
            refs=inventory(p)
            for role,ref in refs.items():
                ref['id']=digest_data([role,ref['sha256']])[:32];ref['role']=role;ref.pop('path')
            history=self.sessions.get((ident,tab))
            active=self.leases.get(ident);editable=bool(active and active['tab']==tab and active['expires']>time.monotonic())
            pref=guard(root,root/'.studio/session.json');preferences=read_json(pref) if pref.is_file() else {}
            return {'id':ident,'revision':revision(root),'version':v,'read_only':v!=2,'project':p.data,
                    'references':list(refs.values()),'observations':obs,
                    'views':{name:{'crop_id':crop_identity(role,data.get('crop')) for role in refs} for name,data in cal.get('views',{}).items()},
                    'roles':p.profile['roles']+p.profile['optional_roles']+['axis','datum','measurement'],
                    'measurements':cal.get('datums',{}).get('measurements',[]),'readiness':readiness(root),
                    'history':{'undo':bool(history and history.undo_stack),'redo':bool(history and history.redo_stack)},
                    'editable':editable,'preferences':preferences}

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
                    allowed={'AddObservation','MoveObservation','DeleteObservation','SetObservationProperties','AddSplinePoint','MoveSplinePoint','DeleteSplinePoint','SplitSpline','MergeSpline','SetMeasurement','SetProjectMetadata','SetProjectSettings','SetViewerLabel'}
                    if not isinstance(commands,list) or not 1<=len(commands)<=100:raise SchemaError('1..100 commands required')
                    for command in commands:
                        if command.get('type') not in allowed or command.get('target','observation')!='observation':raise SchemaError('Operation unavailable in manual source authoring')
                        if command.get('type')=='SetProjectSettings' and command.get('section') not in ('validation','authoring_state'):raise SchemaError('Settings section unavailable in manual authoring')
                    result=session.apply(commands,expected_revision=expected)
                elif operation in ('undo','redo'):result=getattr(session,operation)(expected_revision=expected)
                elif operation=='reload':
                    self.sessions[(ident,tab)]=AuthoringSession(root);result={'revision':expected}
                elif operation=='preferences':
                    # Typed presentation-only allowlist, never a second geometry store.
                    prefs=body.get('preferences',{})
                    self.validate_preferences(prefs)
                    guard(root,root/'.studio/session.json')
                    atomic_write(root,'.studio/session.json',(json.dumps(prefs)+'\n').encode());result={'revision':expected}
                elif operation=='reference-imports':
                    result=import_reference(session,body['_raw'],reference_id=body.get('reference_id','multiview'),expected_revision=expected)
                else:raise APIError(404,'OPERATION','Unsupported operation')
                self.seen[ident]=result['revision'];lease['expires']=time.monotonic()+45
                snapshot=self.snapshot(ident,tab);result={**result,'snapshot':snapshot}
                self.requests[key]=(fingerprint,result)
                if len(self.requests)>512:self.requests.pop(next(iter(self.requests)))
                for kind in ('project_changed','validation_changed','revision_changed'):
                    self.bus.emit(kind,project_id=ident,revision=result['revision'])
                return result

    @staticmethod
    def validate_preferences(prefs):
        from jsonschema import validate
        state={'type':'object','properties':{'visible':{'type':'boolean'},'locked':{'type':'boolean'},'opacity':{'type':'number','minimum':0,'maximum':1},'name':{'type':'string','maxLength':80},'category':{'enum':['image','observations','curves','datums']}},'additionalProperties':False}
        schema={'type':'object','properties':{'active_view':{'enum':['front','side','rear','top']},'reference_id':{'type':'string','maxLength':40},
                'viewport':{'type':'object','properties':{k:{'type':'number','minimum':-1e7,'maximum':1e7} for k in ('x','y','scale')},'additionalProperties':False},
                'layers':{'type':'object','maxProperties':32,'additionalProperties':state},
                'assignments':{'type':'object','maxProperties':20000,'additionalProperties':{'type':'string','maxLength':80}}},'additionalProperties':False}
        try:validate(prefs,schema)
        except Exception as exc:raise SchemaError('Invalid UI preferences: '+getattr(exc,'message','invalid state')) from exc

    def decode_image(self,raw):
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
            except Exception as exc:raise APIError(422,'IMAGE','Corrupt or unsupported reference image') from exc
