"""Bounded asynchronous CV proposals; core alone accepts canonical commands."""
import copy,hashlib,json,re,threading,time,uuid
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
from vehiclerecon.core.project import Project,read_json,validate
from vehiclerecon.core.locking import ProjectLock
from vehiclerecon.core.revisions import revision
from vehiclerecon.core.manifest import digest_data
from vehiclerecon.core.errors import ConflictError,SchemaError
from vehiclerecon.authoring.contracts import crop_identity
from vehiclerecon.authoring.contours import fit_contour
from .providers import ProviderRegistry,OpenCVProvider,ProviderUnavailable
from .cache import ByteCache,size

class Cancelled(Exception):pass

class CVService:
    def __init__(self,registry):
        self.registry=registry;self.providers=ProviderRegistry([OpenCVProvider()]);self.lock=threading.RLock()
        self.worker=ThreadPoolExecutor(max_workers=1,thread_name_prefix='studio-cv')
        self.jobs=OrderedDict();self.proposals=ByteCache(24*1024*1024,64)
        self.results=ByteCache(16*1024*1024,32);self.fields=ByteCache(64*1024*1024,64)
        self.pending_bytes=0;self.closed=False

    def catalog(self):
        result=self.providers.providers()
        for row in result:
            row['available']=row['available'] and self.registry.config.cv_enabled
            row['enabled']=self.registry.config.cv_enabled
        return result

    def _error(self,status,code,message):
        from ..workspace import APIError
        raise APIError(status,code,message)

    def _source(self,ident,expected,request):
        from ..workspace import guard
        reg=self.registry;root=reg.resolve(ident)
        with reg.lock,ProjectLock(root,'cv-source-read'):
            snap=reg.snapshot(ident)
            if expected!=snap['revision']:raise ConflictError('CV source revision changed; reload project')
            ref=next((r for r in snap['references'] if r['id']==request['reference_id']),None)
            if ref is None:self._error(404,'REFERENCE','Unknown project-scoped source reference')
            if ref['size'][0]*ref['size'][1]>16777216:self._error(413,'CV_BUDGET','CV supports at most 16 megapixels per source')
            project=Project(root);path=guard(root,root/project.data['references'][ref['role']])
            if path.stat().st_size>64*1024*1024:self._error(413,'CV_BUDGET','CV encoded source budget exceeded')
            raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ConflictError('Source pixels changed')
            cal_path=project.data.get('generated',{}).get('calibration')
            cal=read_json(guard(root,root/cal_path)) if cal_path else {}
            view=cal.get('views',{}).get(request['view'],{});declared=view.get('crop')
            crop=declared or [0,0,*ref['size']]
            w,h=ref['size']
            if not (0<=crop[0]<crop[2]<=w and 0<=crop[1]<crop[3]<=h):
                self._error(422,'CV_FRAMING','Selected view crop does not fit this reference; choose the calibrated source')
            context={'source_revision':expected,'source_sha256':ref['sha256'],'source_reference_id':ref['id'],
                     'source_role':ref['role'],'source_size':ref['size'],'crop':crop,
                     'crop_id':crop_identity(ref['role'],declared),'view':request['view']}
            return raw,context

    def submit(self,ident,owner,body):
        if set(body)-{'expected_revision','lease_id','request'}:raise SchemaError('Unknown CV job field')
        request=body.get('request',{});validate(request,'cv_request')
        if not self.registry.config.cv_enabled:self._error(503,'PROVIDER_UNAVAILABLE','Provider unavailable: CV disabled at startup')
        try:provider=self.providers.get(request['provider_id'],request['capability'])
        except ProviderUnavailable as exc:self._error(503,'PROVIDER_UNAVAILABLE',str(exc))
        raw,source=self._source(ident,body.get('expected_revision'),request)
        with self.lock:
            active=sum(j['activity']!='FINISHED' for j in self.jobs.values())
            if self.closed or active>=4 or self.pending_bytes+len(raw)>64*1024*1024:
                self._error(429,'CV_BUSY','Bounded CV worker queue is full; cancel or wait for an existing job')
            if 'supersedes' in request:
                self.invalidate(ident,owner,request['supersedes'])
            if 'parent_proposal_id' in request:
                parent=self.get(ident,owner,request['parent_proposal_id'],fence=False)['proposal']
                if parent['source_revision']!=source['source_revision'] or parent['source_sha256']!=source['source_sha256'] or parent['view']!=source['view']:
                    raise ConflictError('Parent proposal belongs to another source context')
            while len(self.jobs)>=128:
                old=next((k for k,j in self.jobs.items() if j['activity']=='FINISHED'),None)
                if old is None:self._error(429,'CV_BUSY','CV job retention full')
                self.jobs.pop(old)
            metadata=provider.metadata();ident_job=uuid.uuid4().hex
            key=digest_data([metadata['provider_id'],metadata['provider_version'],request['capability'],
                             source['source_sha256'],source['crop_id'],request['view'],source['crop'],request['parameters']])
            job={'job_id':ident_job,'project_id':ident,'owner':owner,'activity':'QUEUED','result':None,
                 'progress':0,'proposal_id':None,'source_revision':source['source_revision'],'freshness':'current',
                 'cancel':threading.Event(),'error':None}
            self.jobs[ident_job]=job;self.pending_bytes+=len(raw)
            self.worker.submit(self._work,job,copy.deepcopy(request),source,raw,key,metadata)
            return self._dto(job)

    @staticmethod
    def _dto(job):return {k:v for k,v in job.items() if k not in ('owner','cancel')}

    def _event(self,job):
        self.registry.bus.emit('cv_job_changed',project_id=job['project_id'],job_id=job['job_id'],
                               revision=job['source_revision'],activity=job['activity'],result=job['result'],progress=job['progress'])

    def _work(self,job,request,source,raw,key,metadata):
        began=time.perf_counter()
        def check():
            if job['cancel'].is_set():raise Cancelled()
            if time.perf_counter()-began>45:raise ValueError('Bounded CV operation exceeded 45 seconds')
        try:
            check();job['activity']='RUNNING';job['progress']=.1;self._event(job)
            cached=self.results.get(key);hit=cached is not None
            output=copy.deepcopy(cached) if hit else self.providers.run(request['provider_id'],request['capability'],raw,request['parameters'],
                {'cache':self.fields,'source_hash':source['source_sha256'],'crop':source['crop'],'check':check})
            check();job['progress']=.9;self._event(job)
            if not hit:self.results.put(key,copy.deepcopy(output))
            proposal_id=uuid.uuid4().hex;rasters=output.pop('rasters',{})
            proposal={'proposal_id':proposal_id,'provider_id':metadata['provider_id'],'provider_version':metadata['provider_version'],
                'capability':request['capability'],**source,'parameters':request['parameters'],'created_input_hash':key,
                'status':'ACTIVE','proposal_revision':1,'provenance':{'classification':'local','deterministic':True,
                'semantic_understanding':False,'method':'Optional provider output; explicit ACCEPT required'},
                'rasters':list(rasters),'elapsed_ms':(time.perf_counter()-began)*1000,'cache_hit':hit,**output}
            root=self.registry.resolve(job['project_id'])
            with self.registry.lock,ProjectLock(root,'cv-result-fence'):
                check()
                if revision(root)!=source['source_revision']:
                    proposal['status']='STALE';job['freshness']='stale'
                    for c in proposal['components']:c['status']='STALE'
                validate(proposal,'cv_proposal')
                with self.lock:
                    self.proposals.put(proposal_id,{'owner':job['owner'],'project_id':job['project_id'],'proposal':proposal,'rasters':rasters})
                    job['proposal_id']=proposal_id;job['result']='SUCCEEDED'
        except Cancelled:job['result']='CANCELLED'
        except Exception as exc:
            job['result']='FAILED';job['error']=('Provider failed: '+str(exc))[:500]
        finally:
            with self.lock:
                self.pending_bytes-=len(raw);job['activity']='FINISHED';job['progress']=1
            self._event(job)

    def job(self,ident,owner,job_id):
        with self.lock:
            j=self.jobs.get(job_id)
            if j is None or j['owner']!=owner or j['project_id']!=ident:self._error(404,'CV_JOB','Unknown owned CV job')
            return self._dto(j)

    def cancel(self,ident,owner,job_id):
        with self.lock:
            self.job(ident,owner,job_id);job=self.jobs[job_id]
            if job['activity']!='FINISHED':job['cancel'].set();job['activity']='CANCELLING';self._event(job)
            return self._dto(job)

    def get(self,ident,owner,proposal_id,*,fence=True):
        entry=self.proposals.get(proposal_id)
        if entry is None or entry['owner']!=owner or entry['project_id']!=ident:
            self._error(404,'CV_PROPOSAL','Proposal expired or is not owned by this tab; rerun it')
        p=entry['proposal']
        if fence and p['status']=='ACTIVE':
            root=self.registry.resolve(ident)
            with self.registry.lock,ProjectLock(root,'cv-inspect-fence'):
                if revision(root)!=p['source_revision']:
                    self.invalidate(ident,owner,proposal_id)
        return entry

    def invalidate(self,ident,owner,proposal_id):
        entry=self.get(ident,owner,proposal_id,fence=False);p=entry['proposal']
        if p['status']=='ACTIVE':
            p['status']='STALE';p['proposal_revision']+=1
            for c in p['components']:
                if c['status']=='ACTIVE':c['status']='STALE'
            self.proposals.put(proposal_id,entry)
        return copy.deepcopy(p)

    def reject(self,ident,owner,proposal_id,ids):
        with self.registry.lock:
            entry=self.get(ident,owner,proposal_id);p=entry['proposal']
            if not isinstance(ids,list) or not ids or set(ids)-{c['id'] for c in p['components']}:raise SchemaError('Select existing proposal components')
            for c in p['components']:
                if c['id'] in ids and c['status']=='ACTIVE':c['status']='REJECTED'
            if not any(c['status']=='ACTIVE' for c in p['components']) and p['status']=='ACTIVE':p['status']='REJECTED'
            p['proposal_revision']+=1;self.proposals.put(proposal_id,entry);return copy.deepcopy(p)

    def edit(self,ident,owner,proposal_id,request):
        validate(request,'cv_edit')
        with self.registry.lock:
            entry=self.get(ident,owner,proposal_id);p=copy.deepcopy(entry['proposal'])
            if p['status']!='ACTIVE' or p['proposal_revision']!=request['proposal_revision']:raise ConflictError('Proposal revision changed or is stale')
            c=next((c for c in p['components'] if c['id']==request['component_id'] and c['status']=='ACTIVE'),None)
            if c is None:raise SchemaError('Choose an active component')
            action=request['action']
            if action=='semantic':c['semantic_role']=request.get('semantic_role','UNKNOWN')
            elif c['kind']=='circle':raise SchemaError('Circle candidates are confirmed as source circles; use manual source tools after acceptance')
            else:
                work=copy.deepcopy(c.get('working_points',c['original_points']));closed=c.get('closed',False)
                if action=='reverse':work.reverse()
                elif action=='trim':
                    a=request.get('start',0);b=request.get('end',len(work)-1)
                    if not 0<=a<b<len(work):raise SchemaError('Trim start/end must select at least two existing samples')
                    work=work[a:b+1];closed=False
                elif action in ('open','close'):
                    closed=action=='close'
                    if not closed and work[0]==work[-1]:work.pop()
                elif action=='move_point':
                    index=request.get('index',-1);pixel=request.get('pixel')
                    work=copy.deepcopy(c['points'])
                    if not 0<=index<len(work) or pixel is None:raise SchemaError('Choose an existing proposal point and source pixels')
                    x,y,r,b=p['crop']
                    if not x<=pixel[0]<=r or not y<=pixel[1]<=b:raise SchemaError('Edited point must remain in the selected source crop')
                    work[index]=pixel;c['user_edited']=True
                original=c['original_points']
                try:fit=fit_contour(work,tolerance=request.get('tolerance',c.get('fit',{}).get('tolerance_px',2)),
                    max_points=request.get('max_points',1024),preserve_corners=request.get('preserve_corners',True),
                    spline=request.get('spline',False),closed=closed)
                except ValueError as exc:raise SchemaError(str(exc)) from exc
                c.update(fit,original_points=original,working_points=work)
            p['proposal_revision']+=1;validate(p,'cv_proposal')
            entry={**entry,'proposal':p};self.proposals.put(proposal_id,entry);return copy.deepcopy(p)

    def combine(self,ident,owner,body):
        ids=body.get('proposal_ids',[])
        if set(body)-{'expected_revision','lease_id','proposal_ids'} or not isinstance(ids,list) or not 1<=len(ids)<=32 or len(set(ids))!=len(ids):
            raise SchemaError('Choose 1..32 distinct committed Smart Edge segment proposals')
        with self.registry.lock:
            values=[self.get(ident,owner,i)['proposal'] for i in ids];first=values[0]
            signature=lambda p:[p[k] for k in ('provider_id','provider_version','source_revision','source_sha256','crop_id','view')]
            if first['source_revision']!=body.get('expected_revision') or any(p['status']!='ACTIVE' or p['capability']!='smart_edge' or signature(p)!=signature(first) for p in values):
                raise ConflictError('Trace segments must share one current source/provider context')
            dense=[]
            for p in values:
                c=p['components'][0];part=c.get('working_points',c['original_points'])
                dense.extend(part[1:] if dense and dense[-1]==part[0] else part)
            try:fit=fit_contour(dense,tolerance=first['parameters'].get('tolerance',1),max_points=1024,preserve_corners=False)
            except ValueError as exc:raise SchemaError(str(exc)) from exc
            p=copy.deepcopy(first);p.update(proposal_id=uuid.uuid4().hex,proposal_revision=1,components=[{
                'id':'component_0','status':'ACTIVE','semantic_role':'UNKNOWN','score':None,**fit}],rasters=[])
            p['provenance']={'classification':'local','deterministic':True,'semantic_understanding':False,
                'method':'User committed directed segments; no canonical mutation','segment_input_hashes':[v['created_input_hash'] for v in values],
                'segment_parameters':[v['parameters'] for v in values]}
            p['created_input_hash']=digest_data([p['source_revision'],p['provenance'],fit['original_points']]);validate(p,'cv_proposal')
            self.proposals.put(p['proposal_id'],{'owner':owner,'project_id':ident,'proposal':p,'rasters':{}})
            return copy.deepcopy(p)

    def accept(self,ident,owner,proposal_id,body,key):
        if set(body)-{'expected_revision','lease_id','proposal_revision','component_ids','semantic_roles','confirm_observed','response_format'}:
            raise SchemaError('Unknown CV acceptance field')
        with self.registry.lock:
            if not isinstance(key,str) or not re.fullmatch('[A-Za-z0-9_-]{16,100}',key):
                self._error(428,'IDEMPOTENCY','Idempotency-Key required')
            fingerprint=digest_data(['cv-accept',ident,owner,proposal_id,body]);cached=self.registry.requests.get(key)
            if cached:
                if cached[0]!=fingerprint:raise ConflictError('Idempotency key reused with another CV acceptance')
                return cached[1]
            root=self.registry.resolve(ident)
            with ProjectLock(root,'cv-accept'):
                entry=self.get(ident,owner,proposal_id);p=entry['proposal']
                if p['status']!='ACTIVE' or p['proposal_revision']!=body.get('proposal_revision') or revision(root)!=p['source_revision']:
                    raise ConflictError('Stale or previously decided proposal cannot be accepted; rerun')
                ids=body.get('component_ids',[]);roles=body.get('semantic_roles',{});measured=body.get('confirm_observed',False)
                if not isinstance(ids,list) or not 1<=len(ids)<=16 or len(set(ids))!=len(ids) or not isinstance(roles,dict) or type(measured) is not bool:
                    raise SchemaError('Choose 1..16 distinct components and explicit semantic roles')
                chosen=[c for c in p['components'] if c['id'] in ids and c['status']=='ACTIVE']
                if len(chosen)!=len(ids):raise SchemaError('Only active existing components can be accepted')
                commands=[];new_ids=[]
                for c in chosen:
                    role=roles.get(c['id'],c['semantic_role'])
                    if role=='UNKNOWN':raise SchemaError('Assign an explicit profile semantic role before acceptance')
                    obs_id='cv_'+uuid.uuid4().hex;new_ids.append(obs_id)
                    method=json.dumps({'proposal_id':proposal_id,'component_id':c['id'],'capability':p['capability'],
                        'created_input_hash':p['created_input_hash'],'source_revision':p['source_revision'],
                        'parameters':p['parameters'],'fit':c.get('fit'),'explicit_ACCEPT':True,'source_pixels_verified':measured},separators=(',',':'))
                    observation={'id':obs_id,'view':p['view'],'kind':c['kind'],'semantic_role':role,
                        'reference_id':p['source_role'],'source_sha256':p['source_sha256'],'crop_id':p['crop_id'],'revision':1,
                        'provenance':{'type':'measured' if measured else 'inferred','method':method,
                            'provider':p['provider_id']+'@'+p['provider_version']},
                        'uncertainty_px':max(.25,c.get('fit',{}).get('certified_max_deviation_px',2)),
                        'visibility':'observed' if measured else 'inferred','measured':measured}
                    if c['kind']=='circle':observation.update(center=c['center'],radius_px=c['radius_px'])
                    else:
                        knots=c.get('knots') if c['kind']=='spline' else [{'pixel':v} for v in c['points']]
                        observation['points']=[{'id':'cvk_'+uuid.uuid4().hex,**k} for k in knots]
                    commands.append({'type':'AddObservation','view':p['view'],'observation':observation})
                transaction_key=hashlib.sha256((key+':cv-transaction').encode()).hexdigest()
                result=self.registry.mutate(ident,owner,{'expected_revision':body['expected_revision'],'lease_id':body.get('lease_id'),
                    'commands':commands,'response_format':body.get('response_format','full')},transaction_key,'transactions')
                if self.registry.requests.get(transaction_key):self.registry.requests.pop(transaction_key)
                p['status']='ACCEPTED';p['proposal_revision']+=1
                for c in p['components']:
                    if c['id'] in ids:
                        c['status']='ACCEPTED';c['semantic_role']=roles.get(c['id'],c['semantic_role'])
                    elif c['status']=='ACTIVE':c['status']='STALE'
                self.proposals.put(proposal_id,entry)
                response={**result,'accepted_observation_ids':new_ids,'proposal':copy.deepcopy(p)}
                self.registry.requests[key]=(fingerprint,response)
                return response

    def metrics(self):
        return {'active_jobs':sum(j['activity']!='FINISHED' for j in self.jobs.values()),'pending_source_bytes':self.pending_bytes,
                'proposal_bytes':self.proposals.bytes,'proposal_limit_bytes':self.proposals.limit,'proposal_count':len(self.proposals.items),
                'result_cache_bytes':self.results.bytes,'result_cache_limit_bytes':self.results.limit,
                'image_edge_cache_bytes':self.fields.bytes,'image_edge_cache_limit_bytes':self.fields.limit}

    def close(self):
        self.closed=True
        for j in self.jobs.values():j['cancel'].set()
        self.worker.shutdown(wait=True,cancel_futures=False)
        self.proposals.clear();self.results.clear();self.fields.clear()
