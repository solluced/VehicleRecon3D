"""Project-scoped durable inactive evidence and disposable core-sampled previews."""
import copy,hashlib,io,json,re,time,uuid
from PIL import Image,ImageChops
from vehiclerecon.core.project import Project,read_json,validate
from vehiclerecon.core.revisions import revision
from vehiclerecon.core.manifest import digest_file,digest_data
from vehiclerecon.core.transactions import atomic_write
from vehiclerecon.core.locking import ProjectLock
from vehiclerecon.core.errors import ConflictError,ReferenceError,SchemaError,ReconError
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.reference.reconciliation import make_candidate,evaluate,evidence,model,audit
from vehiclerecon.reference.rectification import PiecewiseMonotonicAxisWarp
from .cv.cache import ByteCache

class Reconciliation:
    def __init__(self,registry):
        self.registry=registry;self.cache=ByteCache(16*1024*1024,24);self.preview_cache=ByteCache(16*1024*1024,16)
    def path(self,ident,candidate_id):
        from .workspace import guard
        if not re.fullmatch('[0-9a-f]{32}',candidate_id):raise ReferenceError('Unknown candidate identity')
        root=self.registry.resolve(ident)
        return guard(root,root/'.studio/rectification'/f'{candidate_id}.json')
    def load(self,ident,candidate_id):
        path=self.path(ident,candidate_id)
        if not path.is_file() or path.stat().st_size>256*1024:raise ReferenceError('Unknown or oversized candidate')
        return read_json(path)
    def store(self,ident,p):
        root=self.registry.resolve(ident);path=self.path(ident,p['id']);raw=(json.dumps(p,allow_nan=False,indent=2)+'\n').encode()
        if len(raw)>256*1024:raise SchemaError('Candidate evidence exceeds 256 KiB; narrow the correspondence set')
        atomic_write(root,path.relative_to(root).as_posix(),raw)
    def legacy(self,ident):
        p=Project(self.registry.resolve(ident));path=p.path('validation/rectification_candidate.json')
        if not path.is_file():return {'read_only':True,'candidates':[],'issue':'No historical rectification evidence'}
        saved=read_json(path);magnitude=read_json(p.path('validation/rectification_magnitude.json',exists=True))
        cal=read_json(p.path(p.data['generated']['calibration'],exists=True));view=saved['affected_view']
        matches=saved['base_calibration_sha256']==digest_file(p.path(p.data['generated']['calibration'])) and saved['source_sha256']==digest_file(p.path(p.data['references']['multiview']))
        plot=audit(saved['rectification'],cal['views'][view]['crop'],wheelbase_m=cal.get('datums',{}).get('stock_body_dimensions_m',{}).get('wheelbase'))
        return {'read_only':True,'view':view,'gauge_view':saved['reference_gauge'],'references':self.registry.snapshot(ident)['references'],
            'candidates':[{'id':'legacy_mark2','status':'REJECTED','active':False,'freshness':'current' if matches else 'STALE',
                'creator':'Existing documented reconciliation','request':{'view':view,'gauge_view':saved['reference_gauge'],**saved['rectification']},
                'report':{**plot,'eligible':False,'status':'REJECTED','distortion':'EXCESSIVE','reasons':['REJECTED / NOT ACTIVE','OUTSIDE SCALE LIMIT',saved['rejection']],
                    'allowed_scale':[.9,1.1],'historical_magnitude':magnitude,'rms_all_landmark_correction_px':magnitude[view]['rms_landmark_correction_px'],
                    'held_out':magnitude[view].get('corrections',[]),'anchors':saved['rectification']['anchors']}}]}
    def context(self,ident,view):
        root=self.registry.resolve(ident)
        with self.registry.lock,ProjectLock(root,'reconciliation-inspect'):
            project=Project(root)
            if project.data['schema_version']!=2:return self.legacy(ident)
            if view not in ('front','side','rear','top'):raise SchemaError('Unknown source view')
            w=Workspace(root);cal=w.documents['calibration'];d=cal['views'][view];rows=evidence(w,view)
            if len(rows)>128:raise SchemaError('Reconciliation supports at most 128 measured correspondences per view')
            left,top,right,bottom=d['crop'];a,b=left,right;anchors=[];bound=set()
            for x,name in ((0,'front_axle'),(1,'rear_axle')):
                match=next((r for r in rows if abs(r['pixel'][0]-(a+x*(b-a)))<1e-9 and abs(r['projected_affine'][0]-(a+x*(b-a)))<1e-9),None)
                anchor={'id':'datum_'+str(x),'semantic':name,'image':x,'world_normalized':x,'role':'FIT','locked':True,'confidence':1,
                    'provenance':'Explicit normalized datum; confirm image/affine domains'}
                if match:anchor['observation_id']=match['observation_id'];bound.add(match['observation_id'])
                anchors.append(anchor)
            for r in rows:
                if r['observation_id'] in bound:continue
                anchors.append({'id':'a_'+hashlib.sha256(r['id'].encode()).hexdigest()[:24],'semantic':r['semantic'],'image':(r['pixel'][0]-a)/(b-a),
                    'world_normalized':(r['projected_affine'][0]-a)/(b-a),'role':'HELD_OUT','locked':False,
                    'confidence':r['provenance'].get('confidence',1),'provenance':r['provenance']['method'],'observation_id':r['observation_id']})
            request={'view':view,'gauge_view':'side' if view!='side' else 'top','reference_role':d.get('reference_id','multiview'),
                'axis':'u','image_domain_px':[a,b],'affine_domain_px':[a,b],'anchors':sorted(anchors,key=lambda r:r['image']),
                'max_scale_change':.1,'allow_extrapolation':False}
            directory=self.path(ident,'0'*32).parent
            paths=list(directory.glob('*.json')) if directory.is_dir() else []
            if len(paths)>256:raise SchemaError('Candidate archive exceeds 256 records')
            candidates=[]
            for path in paths:
                p=self.inspect(ident,path.stem,w=w);report=p['report']
                candidates.append({k:p[k] for k in ('id','revision','status','active','freshness','creator','view')})
                candidates[-1]['summary']={k:report.get(k) for k in ('eligible','distortion','whole_crop','local_scale_range','before','after','extrapolation')}
            return {'read_only':False,'view':view,'revision':w.revision,'default_request':request,'evidence':rows,
                'calibration':d,'references':self.registry.snapshot(ident)['references'],'candidates':candidates}
    def inspect(self,ident,candidate_id,*,w=None):
        p=self.load(ident,candidate_id);root=self.registry.resolve(ident);rev=revision(root)
        key=(ident,candidate_id,p['revision']);report=self.cache.get(key)
        if report is None:report=evaluate(p);self.cache.put(key,report)
        same=rev==p['source_revision'];active=False
        if p['status']=='ACTIVE':
            project=Project(root);cal=read_json(project.path(project.data['generated']['calibration']))
            active=cal['views'][p['view']].get('rectification')==model(p['request'])
        status='ACTIVE' if active else 'REJECTED' if p['status']=='REJECTED' else report['status'] if same else 'STALE'
        return {**p,'status':status,'active':active,'freshness':'current' if same or active else 'STALE','report':copy.deepcopy(report)}
    def create(self,ident,body):
        if set(body)-{'expected_revision','request','creator','confirm_datums'}:raise SchemaError('Unknown candidate generation field')
        if not isinstance(body.get('creator'),str) or not 1<=len(body['creator'].strip())<=300:raise SchemaError('Candidate creator required')
        root=self.registry.resolve(ident)
        with self.registry.lock,ProjectLock(root,'reconciliation-candidate'):
            if revision(root)!=body.get('expected_revision'):raise ConflictError('Candidate source changed')
            w=Workspace(root);request=body['request'];validate(request,'reconciliation_request')
            default=w.documents['calibration']['views'][request['view']]['crop'];axis=0 if request['axis']=='u' else 1
            domain=[default[axis],default[axis+2]]
            if (request['image_domain_px']!=domain or request['affine_domain_px']!=domain) and body.get('confirm_datums') is not True:
                raise SchemaError('Changing datum domains requires separate explicit confirmation')
            directory=self.path(ident,'0'*32).parent
            if directory.is_dir() and len(list(directory.glob('*.json')))>=256:raise SchemaError('Candidate archive full (256); export/archive evidence outside Studio before creating more')
            p=make_candidate(w,request,ident=uuid.uuid4().hex,creator=body['creator'].strip())
            self.store(ident,p);return self.inspect(ident,p['id'])
    def reject(self,ident,candidate_id,body):
        if set(body)-{'candidate_revision','reason'} or not isinstance(body.get('reason'),str) or not 1<=len(body['reason'].strip())<=1000:
            raise SchemaError('An explicit rejection reason is required')
        root=self.registry.resolve(ident)
        with self.registry.lock,ProjectLock(root,'reconciliation-reject'):
            p=self.load(ident,candidate_id)
            if p['revision']!=body.get('candidate_revision'):raise ConflictError('Candidate revision changed')
            if self.inspect(ident,candidate_id)['active']:raise ConflictError('Undo active calibration before rejecting its candidate')
            p.update(status='REJECTED',reason=body['reason'].strip(),revision=p['revision']+1);self.store(ident,p)
            return self.inspect(ident,candidate_id)
    def activation_command(self,ident,body):
        if body.get('confirm_activation') is not True:raise SchemaError('Explicit activation confirmation required')
        p=self.load(ident,body['candidate_id'])
        if p['revision']!=body.get('candidate_revision'):raise ConflictError('Candidate revision changed')
        return {'type':'ActivateRectification','candidate':{k:p[k] for k in ('id','status','source_revision','base_calibration_hash','source_hashes','creator','request')}}
    def mark_active(self,ident,candidate_id,revision_value):
        p=self.load(ident,candidate_id)
        if p.get('activation_revision')!=revision_value:
            p.update(status='ACTIVE',activation_revision=revision_value,revision=p['revision']+1);self.store(ident,p)
    def preview(self,ident,candidate_id,kind):
        if kind not in ('raw','rectified','difference'):raise ReferenceError('Unknown preview kind')
        root=self.registry.resolve(ident);project=Project(root)
        if candidate_id=='legacy_mark2':
            legacy=self.legacy(ident);p=legacy['candidates'][0];r=p['request'];crop=read_json(project.path(project.data['generated']['calibration']))['views'][r['view']]['crop'];role='multiview';expected=read_json(project.path('validation/rectification_candidate.json'))['source_sha256']
        else:
            p=self.load(ident,candidate_id);r=p['request'];crop=p['crop'];role=r['reference_role'];expected=p['source_hashes'][role]
        path=project.path(project.data['references'][role],exists=True)
        if digest_file(path)!=expected:raise ConflictError('Pinned source pixels changed; historical preview unavailable')
        key=(expected,digest_data(r),tuple(crop),kind);cached=self.preview_cache.get(key)
        if cached is not None:return cached
        rect=r if candidate_id=='legacy_mark2' else model(r)
        warp=PiecewiseMonotonicAxisWarp([a['image'] for a in rect['anchors']],[a['world_normalized'] for a in rect['anchors']])
        a,b=rect['image_domain_px'];c,d=rect['affine_domain_px'];axis=0 if rect['axis']=='u' else 1
        with Image.open(path) as image:
            if image.width*image.height>16777216:raise ReferenceError('Preview supports at most 16 megapixels')
            image.load();source=image.convert('RGB').crop(tuple(crop))
        factor=min(1,1024/source.width,1024/source.height);size=(max(1,round(source.width*factor)),max(1,round(source.height*factor)))
        raw=source.resize(size,Image.Resampling.BILINEAR);mesh=[]
        for i in range(size[axis]):
            lo=(crop[axis]+i/factor-c)/(d-c);hi=(crop[axis]+(i+1)/factor-c)/(d-c)
            u=(a+(b-a)*warp.inverse(lo)-crop[axis])*factor;v=(a+(b-a)*warp.inverse(hi)-crop[axis])*factor
            if axis==0:mesh.append(((i,0,i+1,size[1]),(u,0,u,size[1],v,size[1],v,0)))
            else:mesh.append(((0,i,size[0],i+1),(0,u,0,v,size[0],v,size[0],u)))
        rectified=raw.transform(size,Image.Transform.MESH,mesh,Image.Resampling.BILINEAR)
        output=raw if kind=='raw' else rectified if kind=='rectified' else ImageChops.difference(raw,rectified)
        stream=io.BytesIO();output.save(stream,format='PNG');data=stream.getvalue();self.preview_cache.put(key,data);return data
    def metrics(self):return {'candidate_report_bytes':self.cache.bytes,'candidate_report_limit_bytes':self.cache.limit,
        'preview_bytes':self.preview_cache.bytes,'preview_limit_bytes':self.preview_cache.limit,'archive_record_limit':256}
