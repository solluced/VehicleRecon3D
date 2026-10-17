"""FastAPI transports intent; shared core owns canonical validation and writes."""
import asyncio
import json
import re
import secrets
import time
import math
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, FileResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool
from vehiclerecon.core.errors import ReconError, ConflictError, LockError
from vehiclerecon.core.project import Project, RESOURCE_ROOT, read_json
from vehiclerecon.core.revisions import revision
from vehiclerecon.core.manifest import digest_file, digest_data
from vehiclerecon.core.locking import ProjectLock
from vehiclerecon.authoring.service import AuthoringSession
from vehiclerecon.authoring.versions import create_draft
from .security import Security
from .workspace import Registry, APIError, guard


def create_app(config):
    registry=Registry(config);sessions={};streams={}
    @asynccontextmanager
    async def lifespan(application):
        try:yield
        finally:
            application.state.stopping=True
            await run_in_threadpool(registry.cv.close)
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None,debug=False,lifespan=lifespan)
    app.state.registry=registry;app.state.config=config;app.state.stopping=False
    app.add_middleware(Security,config=config,sessions=sessions)

    @app.exception_handler(APIError)
    async def api_error(request,exc):return JSONResponse({'code':exc.code,'message':exc.message,'issues':[]},status_code=exc.status)

    @app.exception_handler(ReconError)
    async def core_error(request,exc):
        status=423 if isinstance(exc,LockError) else 409 if isinstance(exc,ConflictError) else 422
        # Technical core messages may contain local paths; primary feedback is bounded.
        message=str(exc)
        for root in config.roots:message=message.replace(str(root),'<project root>')
        message=message.replace(str(RESOURCE_ROOT),'<installed resources>')
        concise=message[:1200] if len(message)<=200 else 'The selected entity or setting is invalid. Correct its values and try again.'
        return JSONResponse({'code':'LOCKED' if status==423 else 'STALE_REVISION' if status==409 else 'VALIDATION',
            'message':concise,'issues':[{'document':'authoring','pointer':'/commands','message':message[:1200]}],'retryable':status in (409,423)},status_code=status)

    @app.exception_handler(Exception)
    async def internal_error(request,exc):
        return JSONResponse({'code':'INTERNAL','message':'Operation could not complete. Reload the project or restart Studio.',
                             'diagnostic_id':uuid.uuid4().hex,'issues':[]},status_code=500)

    def tab(request):
        ident=request.headers.get('x-studio-tab','')
        if not re.fullmatch('[0-9a-f-]{32,36}',ident):raise APIError(400,'TAB','Valid tab identity required')
        return request.scope['studio_session']['id']+':'+ident

    def precondition(request,body):
        expected=body.get('expected_revision')
        if not expected or request.headers.get('if-match','').strip('"')!=expected:
            raise APIError(428,'REVISION','Matching If-Match and expected_revision required')

    @app.post('/api/v1/session/bootstrap')
    async def bootstrap(request:Request):
        if request.headers.get('content-type','').split(';')[0]!='application/json':raise APIError(415,'TYPE','JSON required')
        body=await request.json()
        if not config.bootstrap or time.monotonic()-config.created>300 or not secrets.compare_digest(str(body.get('secret','')).encode('utf-8'),config.bootstrap.encode('utf-8')):
            raise APIError(401,'BOOTSTRAP','Bootstrap is invalid, expired or already used. Restart Studio for a new launch.')
        config.bootstrap='';token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
        sessions[token]={'id':uuid.uuid4().hex,'csrf':csrf,'created':time.monotonic()}
        response=JSONResponse({'csrf':csrf,'epoch':registry.bus.epoch})
        response.set_cookie('vr_session',token,httponly=True,samesite='strict',path='/api/v1',max_age=12*3600)
        return response

    @app.get('/api/v1/session')
    def session_info(request:Request):return {'csrf':request.scope['studio_session']['csrf'],'epoch':registry.bus.epoch}

    @app.get('/api/v1/roots')
    def roots():return [{'id':k,'label':p.name,'revision':registry.root_revision(k)} for k,p in registry.roots.items()]

    @app.get('/api/v1/capabilities')
    def capabilities():return {'version':'0.3','document_versions':[1,2],'writable_versions':[2],'image_formats':['PNG','JPEG'],
        'max_upload_bytes':config.max_upload,'max_pixels':config.max_pixels,'pipeline':False,
        'CV':any(p['available'] for p in registry.cv.catalog()),'epoch':registry.bus.epoch,'idempotency_survives_restart':False}

    @app.get('/api/v1/cv/providers')
    def cv_providers():return {'providers':registry.cv.catalog(),'limits':{'queue':4,'source_pixels':16777216,'local_search_pixels':262144,'mask_roi_pixels':4194304}}

    @app.get('/api/v1/reconciliation/retention')
    def reconciliation_retention():return registry.reconciliation.metrics()

    @app.get('/api/v1/projects/{ident}/reconciliation')
    def reconciliation_context(ident:str,view:str='top'):return JSONResponse(registry.reconciliation.context(ident,view))

    @app.get('/api/v1/projects/{ident}/reconciliation/{candidate_id}')
    def reconciliation_inspect(ident:str,candidate_id:str):return JSONResponse(registry.reconciliation.inspect(ident,candidate_id))

    @app.post('/api/v1/projects/{ident}/reconciliation')
    def reconciliation_create(ident:str,request:Request,body:dict):
        precondition(request,body);return JSONResponse(registry.reconciliation.create(ident,body))

    @app.post('/api/v1/projects/{ident}/reconciliation/{candidate_id}/reject')
    def reconciliation_reject(ident:str,candidate_id:str,body:dict):
        return JSONResponse(registry.reconciliation.reject(ident,candidate_id,body))

    @app.post('/api/v1/projects/{ident}/activate-rectification')
    def reconciliation_activate(ident:str,request:Request,body:dict):
        precondition(request,body)
        if set(body)-{'expected_revision','lease_id','candidate_id','candidate_revision','confirm_activation','response_format'}:raise APIError(422,'FIELDS','Unknown activation field')
        result=registry.mutate(ident,tab(request),body,request.headers.get('idempotency-key'),'activate-rectification')
        registry.reconciliation.mark_active(ident,body['candidate_id'],result['revision'])
        return JSONResponse(result)

    @app.get('/api/v1/projects/{ident}/reconciliation/{candidate_id}/preview/{kind}')
    def reconciliation_preview(ident:str,candidate_id:str,kind:str):
        return Response(registry.reconciliation.preview(ident,candidate_id,kind),media_type='image/png')

    @app.get('/api/v1/cv/retention')
    def cv_retention():return registry.cv.metrics()

    @app.get('/api/v1/projects/{ident}/cv-context')
    def cv_context(ident:str,request:Request,reference_id:str,view:str,expected_revision:str):
        if view not in ('front','side','rear','top'):raise APIError(422,'VIEW','Unknown source view')
        _,source=registry.cv._source(ident,expected_revision,{'reference_id':reference_id,'view':view})
        return source

    @app.post('/api/v1/projects/{ident}/cv-traces')
    def cv_trace(ident:str,request:Request,body:dict):
        precondition(request,body);return JSONResponse(registry.cv.combine(ident,tab(request),body))

    @app.post('/api/v1/projects/{ident}/cv-jobs')
    def cv_submit(ident:str,request:Request,body:dict):
        precondition(request,body);return JSONResponse(registry.cv.submit(ident,tab(request),body),status_code=202)

    @app.get('/api/v1/projects/{ident}/cv-jobs/{job_id}')
    def cv_job(ident:str,job_id:str,request:Request):return registry.cv.job(ident,tab(request),job_id)

    @app.post('/api/v1/projects/{ident}/cv-jobs/{job_id}/cancel')
    def cv_cancel(ident:str,job_id:str,request:Request,body:dict):return registry.cv.cancel(ident,tab(request),job_id)

    @app.get('/api/v1/projects/{ident}/cv-proposals/{proposal_id}')
    def cv_proposal(ident:str,proposal_id:str,request:Request):
        return JSONResponse(registry.cv.get(ident,tab(request),proposal_id)['proposal'])

    @app.post('/api/v1/projects/{ident}/cv-proposals/{proposal_id}/{action}')
    def cv_decide(ident:str,proposal_id:str,action:str,request:Request,body:dict):
        owner=tab(request)
        if action=='accept':
            precondition(request,body)
            return JSONResponse(registry.cv.accept(ident,owner,proposal_id,body,request.headers.get('idempotency-key')))
        if action=='reject':return JSONResponse(registry.cv.reject(ident,owner,proposal_id,body.get('component_ids')))
        if action=='edit':return JSONResponse(registry.cv.edit(ident,owner,proposal_id,body.get('edit',{})))
        if action=='stale':return JSONResponse(registry.cv.invalidate(ident,owner,proposal_id))
        raise APIError(404,'CV_ACTION','Unknown proposal action')

    @app.get('/api/v1/projects/{ident}/cv-proposals/{proposal_id}/rasters/{kind}')
    def cv_raster(ident:str,proposal_id:str,kind:str,request:Request):
        entry=registry.cv.proposals.get(proposal_id)
        if entry is None or entry['project_id']!=ident or entry['owner'].split(':')[0]!=request.scope['studio_session']['id']:
            raise APIError(404,'CV_RASTER','Unknown project-scoped diagnostic raster')
        raw=entry['rasters'].get(kind)
        if raw is None:raise APIError(404,'CV_RASTER','Unknown proposal raster')
        return Response(raw,media_type='image/png')

    @app.get('/api/v1/schemas')
    def schemas():
        return {'schemas':{p.stem.removesuffix('.schema'):read_json(p) for p in (RESOURCE_ROOT/'schemas').glob('*.schema.json')},
                'profiles':{p.stem:read_json(p) for p in (RESOURCE_ROOT/'profiles').glob('*.json')}}

    @app.get('/api/v1/projects')
    def projects():
        registry.scan();result=[]
        for ident in list(registry.projects):
            try:
                snap=registry.snapshot(ident)
                result.append({k:snap.get(k) for k in ('id','revision','version','read_only','project','readiness','issues')})
            except (ReconError,APIError,OSError,ValueError):
                result.append({'id':ident,'read_only':True,'issues':['Project unavailable or invalid; inspect files outside Studio.']})
        return result

    @app.post('/api/v1/projects')
    def create_project(request:Request,body:dict):
        precondition(request,body);root_id=body.get('root_id')
        if set(body)-{'root_id','name','profile','dimensions','expected_revision'}:raise APIError(422,'FIELDS','Unknown project creation field')
        if root_id not in registry.roots:raise APIError(404,'ROOT','Unknown allowed root')
        name=body.get('name','')
        if not re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,63}',name) or re.fullmatch('(con|prn|aux|nul|com[1-9]|lpt[1-9])',name,re.I):
            raise APIError(422,'NAME','Use letters, numbers, underscores or hyphens; reserved device names are unavailable')
        profile=body.get('profile','sedan')
        if not re.fullmatch('[a-z_]+',profile) or not (RESOURCE_ROOT/'profiles'/f'{profile}.json').is_file():raise APIError(422,'PROFILE','Unknown core profile')
        dims=body.get('dimensions',{})
        if not isinstance(dims,dict) or set(dims)-{'length_m','width_m','height_m','wheelbase_m'}:raise APIError(422,'DIMENSIONS','Unknown dimension')
        for value in dims.values():
            if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0):raise APIError(422,'DIMENSIONS','Dimensions must be positive or unknown')
        root=registry.roots[root_id]
        with registry.lock:
            key=request.headers.get('idempotency-key','')
            if not re.fullmatch('[A-Za-z0-9_-]{16,100}',key):raise APIError(428,'IDEMPOTENCY','Idempotency-Key required')
            fingerprint=digest_data(['create',tab(request),body]);cached=registry.requests.get(key)
            if cached:
                if cached[0]!=fingerprint:raise ConflictError('Idempotency key reused with a different request')
                return cached[1]
            if registry.root_revision(root_id)!=body['expected_revision']:raise ConflictError('Project root changed; refresh project list')
            path=guard(root,root/name.lower())
            if path.exists() or any(p.name.casefold()==name.casefold() for p in root.iterdir()):raise ConflictError('Project already exists')
            create_draft(path,profile=profile);author=AuthoringSession(path)
            commands=[{'type':'SetProjectMetadata','values':{'asset_name':name}}]
            for dimension,value in dims.items():
                if value is not None:commands.append({'type':'SetMeasurement','dimension':dimension,'measurement':{'id':'measure_'+dimension,'value':value,'unit':'m','meaning':dimension,
                    'provenance':{'type':'approximate','method':'User entered at project creation; authority not independently verified'}}})
            author.apply(commands,expected_revision=author.revision)
            registry.scan();ident=next(k for k,v in registry.projects.items() if v==path)
            registry.bus.emit('project_changed',project_id=ident,revision=revision(path))
            result=registry.snapshot(ident);registry.requests[key]=(fingerprint,result)
            if len(registry.requests)>512:registry.requests.pop(next(iter(registry.requests)))
            return result

    @app.get('/api/v1/projects/{ident}')
    def inspect_project(ident:str,request:Request):
        snap=registry.snapshot(ident,tab(request));return JSONResponse(snap,headers={'ETag':'"'+snap['revision']+'"'})

    @app.get('/api/v1/projects/{ident}/revision')
    def current_revision(ident:str):
        with registry.lock,ProjectLock(registry.resolve(ident),'studio-revision-read'):
            return {'revision':revision(registry.resolve(ident))}

    @app.get('/api/v1/projects/{ident}/readiness')
    def project_readiness(ident:str):return registry.snapshot(ident)['readiness']

    @app.get('/api/v1/projects/{ident}/observations')
    def project_observations(ident:str):return registry.snapshot(ident)['observations']

    @app.get('/api/v1/projects/{ident}/analysis')
    def analysis(ident:str,expected_revision:str|None=None):return JSONResponse(registry.analysis(ident,expected_revision))

    @app.get('/api/v1/projects/{ident}/residuals')
    def residuals(ident:str):return JSONResponse(registry.analysis(ident)['residuals'])

    @app.get('/api/v1/projects/{ident}/cage-preview')
    def cage_preview(ident:str):return JSONResponse(registry.analysis(ident)['scene'])

    @app.get('/api/v1/projects/{ident}/correspondences')
    def correspondences(ident:str):return JSONResponse(registry.analysis(ident)['correspondences'])

    @app.get('/api/v1/projects/{ident}/world-landmarks')
    def world_landmarks(ident:str):return JSONResponse(registry.analysis(ident)['world_landmarks'])

    @app.post('/api/v1/projects/{ident}/fit-proposals')
    def fit_proposals(ident:str,request:Request,body:dict):
        precondition(request,body)
        return JSONResponse(registry.propose(ident,tab(request),body))

    @app.post('/api/v1/projects/{ident}/leases')
    def lease(ident:str,request:Request,body:dict):
        precondition(request,body);return registry.acquire(ident,tab(request),body['expected_revision'])

    @app.post('/api/v1/projects/{ident}/release')
    def release(ident:str,request:Request,body:dict):
        precondition(request,body)
        with registry.lock,ProjectLock(registry.resolve(ident),'studio-lease-release'):
            if revision(registry.resolve(ident))!=body['expected_revision']:raise ConflictError('Project changed before lease release')
            active=registry.leases.get(ident)
            if active and active['tab']==tab(request) and active['id']==body.get('lease_id'):registry.leases.pop(ident)
        return {'revision':body['expected_revision']}

    @app.post('/api/v1/projects/{ident}/transactions')
    @app.post('/api/v1/projects/{ident}/undo')
    @app.post('/api/v1/projects/{ident}/redo')
    @app.post('/api/v1/projects/{ident}/reload')
    @app.post('/api/v1/projects/{ident}/preferences')
    @app.post('/api/v1/projects/{ident}/apply-fit')
    @app.post('/api/v1/projects/{ident}/source-review')
    @app.post('/api/v1/projects/{ident}/cage-review')
    def mutate(ident:str,request:Request,body:dict):
        if request.headers.get('content-type','').split(';')[0]!='application/json':raise APIError(415,'TYPE','JSON required')
        precondition(request,body)
        return JSONResponse(registry.mutate(ident,tab(request),body,request.headers.get('idempotency-key'),request.url.path.split('/')[-1]))

    @app.post('/api/v1/projects/{ident}/reference-imports')
    async def import_image(ident:str,request:Request):
        raw=await request.body();await run_in_threadpool(registry.decode_image,raw)
        body={'expected_revision':request.headers.get('x-expected-revision'),'lease_id':request.headers.get('x-editor-lease'),
              'reference_id':request.headers.get('x-reference-role','multiview'),'_raw':raw}
        replacement=request.headers.get('x-replacement-view')
        if replacement:
            if request.headers.get('x-confirm-replacement')!='true' or replacement not in ('front','side','rear','top'):raise APIError(422,'REPLACEMENT','Explicit replacement view and confirmation required')
            body['view']=replacement
        precondition(request,body)
        root=registry.resolve(ident)
        size=sum(p.stat().st_size for p in guard(root,root/'input').glob('*') if p.is_file())
        if size+len(raw)>config.workspace_quota:raise APIError(413,'QUOTA','Reference workspace quota exceeded')
        return await run_in_threadpool(registry.mutate,ident,tab(request),body,request.headers.get('idempotency-key'),'source-replacement' if replacement else 'reference-imports')

    @app.get('/api/v1/projects/{ident}/references/{ref_id}/image')
    def image(ident:str,ref_id:str):
        root=registry.resolve(ident)
        with registry.lock,ProjectLock(root,'studio-reference-read'):
            snap=registry.snapshot(ident);ref=next((r for r in snap['references'] if r['id']==ref_id),None)
            if ref is None:raise APIError(404,'REFERENCE','Unknown reference')
            p=Project(root);path=guard(root,root/p.data['references'][ref['role']]);raw=path.read_bytes()
            import hashlib
            if hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ConflictError('Reference changed; reload project')
            return Response(raw,media_type='image/png' if raw.startswith(b'\x89PNG') else 'image/jpeg',headers={'ETag':'"'+ref['sha256']+'"'})

    @app.get('/api/v1/events')
    async def events(request:Request,tab_id:str):
        if not re.fullmatch('[0-9a-f-]{32,36}',tab_id):raise APIError(400,'TAB','Valid tab identity required')
        key=request.scope['studio_session']['id']+':'+tab_id;owner=uuid.uuid4().hex;streams[key]=owner
        async def stream():
            cursor=request.headers.get('last-event-id')
            try:
                while not app.state.stopping and streams.get(key)==owner and time.monotonic()-request.scope['studio_session']['created']<12*3600 and not await request.is_disconnected():
                    for ident in list(registry.projects):
                        try:
                            def probe():
                                root=registry.resolve(ident)
                                with registry.lock,ProjectLock(root,'studio-revision-watch'):
                                    rev=revision(root)
                                    if ident in registry.seen and registry.seen[ident]!=rev:
                                        registry.bus.emit('conflict',project_id=ident,revision=rev,reason='External canonical change')
                                        registry.bus.emit('revision_changed',project_id=ident,revision=rev)
                                    registry.seen[ident]=rev
                            await run_in_threadpool(probe)
                        except (ReconError,APIError,OSError,ValueError):pass
                    records=registry.bus.replay(cursor)
                    for event in records:
                        cursor=event['id'];yield 'id: '+cursor+'\nevent: '+event['kind']+'\ndata: '+json.dumps(event)+'\n\n'
                    if not records:yield ': keepalive\n\n'
                    await asyncio.sleep(.75)
            finally:
                if streams.get(key)==owner:streams.pop(key,None)
        return StreamingResponse(stream(),media_type='text/event-stream',headers={'X-Accel-Buffering':'no'})

    @app.get('/')
    def index():
        path=config.static/'index.html'
        if not path.is_file():raise APIError(503,'FRONTEND','Build the Studio frontend before launch; see studio_development.md')
        return FileResponse(path)

    @app.get('/assets/{name}')
    def asset(name:str):
        if not re.fullmatch('[A-Za-z0-9_.-]+',name):raise APIError(404,'ASSET','Unknown application asset')
        path=guard(config.static,config.static/'assets'/name)
        if not path.is_file():raise APIError(404,'ASSET','Unknown application asset')
        return FileResponse(path)

    return app
