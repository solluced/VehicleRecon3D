import copy,json,shutil,time,uuid
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient
from vehiclerecon.core.project import REPOSITORY
from vehiclerecon.core.revisions import revision,snapshot
from vehiclerecon.core.manifest import digest_file
from vehiclerecon.authoring.contracts import crop_identity
from vehiclerecon_studio.security import Config
from vehiclerecon_studio.app import create_app
from vehiclerecon_studio.cv.cache import ByteCache
from vehiclerecon_studio.cv.providers import CVProvider,ProviderRegistry,OpenCVProvider,ProviderUnavailable

FIXTURES=REPOSITORY/'tests/fixtures/cv'

@pytest.fixture
def env(tmp_path):
    shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',tmp_path/'study')
    # Keep the positive calibrated fixture's actual source and four critical rows.
    root=tmp_path/'study';config=Config((tmp_path,),9173);app=create_app(config)
    with TestClient(app,base_url=config.origin) as c:
        token=c.post('/api/v1/session/bootstrap',json={'secret':config.bootstrap},headers={'Origin':config.origin}).json()
        h={'Origin':config.origin,'X-CSRF-Token':token['csrf'],'X-Studio-Tab':uuid.uuid4().hex}
        ident=c.get('/api/v1/projects').json()[0]['id'];rev=revision(root)
        lease=c.post(f'/api/v1/projects/{ident}/leases',json={'expected_revision':rev},headers={**h,'If-Match':rev}).json()['lease_id']
        def post(op,**fields):
            rev=revision(root)
            return c.post(f'/api/v1/projects/{ident}/{op}',json={'expected_revision':rev,'lease_id':lease,**fields},headers={**h,'If-Match':rev,'Idempotency-Key':uuid.uuid4().hex})
        def get(op=''):return c.get(f'/api/v1/projects/{ident}'+('/'+op if op else ''),headers=h)
        yield c,app,post,get,root,ident,h,lease

def _run(provider,filename,capability,parameters=None):
    pytest.importorskip('cv2');path=FIXTURES/filename
    return provider.run(capability,path.read_bytes(),parameters or {},
        {'source_hash':digest_file(path),'crop':[0,0,256,256],'cache':ByteCache(),'check':lambda:None})

def test_registry_discovery_unavailable_and_no_implicit_fallback():
    registry=ProviderRegistry([OpenCVProvider()]);meta=registry.providers()[0]
    assert meta['classification']=='local' and meta['deterministic']
    assert {'smart_edge','segment_object','detect_wheels'}<=set(meta['capabilities'])
    with pytest.raises(ProviderUnavailable):registry.get('nonexistent','detect_edges')
    with pytest.raises(ValueError):registry.register(OpenCVProvider())

def test_edges_directed_path_and_false_positive_remain_unknown():
    provider=OpenCVProvider();edges=_run(provider,'strong_edge.png','detect_edges')
    assert edges['rasters']['edges'].startswith(b'\x89PNG') and not edges['components']
    path=_run(provider,'strong_edge.png','smart_edge',{'trajectory':[[123,30],[126,90],[124,190]],'search_radius':12})
    points=np.array(path['components'][0]['points'])
    assert np.max(np.abs(points[:,0]-128))<5 and path['search_pixels']<=262144
    assert path['components'][0]['semantic_role']=='UNKNOWN'
    result=_run(provider,'false_positive.png','trace_contour')
    assert result['components'] and all(c['semantic_role']=='UNKNOWN' for c in result['components'])
    with pytest.raises(ValueError,match='start'):_run(provider,'strong_edge.png','smart_edge',{'trajectory':[[128,30]]})

def test_mask_refinement_and_circle_candidates_source_pixel_coordinates():
    provider=OpenCVProvider();p={'roi':[15,40,245,205]}
    result=_run(provider,'body_mask.png','segment_object',p)
    assert result['components'] and result['mask']['foreground_pixels']>9000
    correction={**p,'strokes':[{'label':'background','points':[[130,130]],'radius':12}]}
    changed=_run(provider,'body_mask.png','segment_object',correction)
    assert changed['mask']['foreground_pixels']<result['mask']['foreground_pixels']
    circles=_run(provider,'circle_wheels.png','detect_wheels',{'roi':[20,90,240,200],'min_radius':18,'max_radius':36})['components']
    assert len(circles)==2 and all(c['kind']=='circle' for c in circles)
    assert [c['center'][0] for c in circles]==pytest.approx([70,185],abs=2)
    assert all(c['semantic_role']=='UNKNOWN' and 'not probability' in c['score_meaning'] for c in circles)

def _source(env,filename):
    _,_,_,get,root,_,_,_=env
    target=root/'input/reference.png';target.write_bytes((FIXTURES/filename).read_bytes())
    path=root/'generated/calibration.json';cal=json.loads(path.read_text());cal['source_sha256']=digest_file(target)
    for view in cal['views'].values():
        for obs in view['landmarks']['observations']:obs['source_sha256']=cal['source_sha256']
    path.write_text(json.dumps(cal)+'\n')
    snap=get().json();return snap['references'][0]['id']

def _proposal(env,filename='circle_wheels.png',capability='detect_wheels',parameters=None):
    _,_,post,get,_,_,_,_=env;ref=_source(env,filename)
    r=post('cv-jobs',request={'provider_id':'opencv','capability':capability,'reference_id':ref,'view':'side','parameters':parameters or {}})
    assert r.status_code==202,r.text
    job=r.json()
    for _ in range(300):
        job=get('cv-jobs/'+job['job_id']).json()
        if job['activity']=='FINISHED':break
        time.sleep(.01)
    assert job['result']=='SUCCEEDED',job
    return get('cv-proposals/'+job['proposal_id']).json()

def test_proposal_partial_accept_source_only_undo_and_reject_noop(env):
    pytest.importorskip('cv2');_,_,post,get,root,*_=env
    p=_proposal(env);before=snapshot(root);world=get('analysis').json()['world_landmarks']
    assert len(p['components'])>=2 and revision(root)==p['source_revision']
    ids=[c['id'] for c in p['components']]
    assert post('cv-proposals/'+p['proposal_id']+'/reject',component_ids=[ids[-1]]).status_code==200
    assert snapshot(root)==before
    p=get('cv-proposals/'+p['proposal_id']).json()
    r=post('cv-proposals/'+p['proposal_id']+'/accept',proposal_revision=p['proposal_revision'],component_ids=[ids[0]],semantic_roles={ids[0]:'wheel'})
    assert r.status_code==200,r.text
    assert len(r.json()['accepted_observation_ids'])==1
    obs=next(o for o in get().json()['observations'] if o['id']==r.json()['accepted_observation_ids'][0])
    assert obs['kind']=='circle' and obs['view']=='side' and obs['visibility']=='inferred' and not obs['measured']
    assert get('analysis').json()['world_landmarks']==world
    assert post('undo').status_code==200 and snapshot(root)==before

def test_stale_crop_source_context_parameters_and_acceptance_fence(env):
    pytest.importorskip('cv2');_,_,post,get,root,*_=env;p=_proposal(env)
    assert post('cv-proposals/'+p['proposal_id']+'/stale').status_code==200
    ids=[p['components'][0]['id']]
    r=post('cv-proposals/'+p['proposal_id']+'/accept',proposal_revision=p['proposal_revision'],component_ids=ids,semantic_roles={ids[0]:'wheel'})
    assert r.status_code==409
    p=_proposal(env);path=root/'project.json';path.write_bytes(path.read_bytes()+b'\n')
    assert get('cv-proposals/'+p['proposal_id']).json()['status']=='STALE'
    assert post('cv-proposals/'+p['proposal_id']+'/accept',proposal_revision=p['proposal_revision'],component_ids=ids,semantic_roles={ids[0]:'wheel'}).status_code==409

def test_proposal_edit_fit_semantics_and_rejection_leave_reviews_current(env):
    pytest.importorskip('cv2');_,_,post,get,root,*_=env;p=_proposal(env,'curved_contour.png','trace_contour')
    before=snapshot(root);cid=p['components'][0]['id']
    r=post('cv-proposals/'+p['proposal_id']+'/edit',edit={'component_id':cid,'proposal_revision':p['proposal_revision'],'action':'fit','spline':True,'tolerance':2,'max_points':128,'preserve_corners':False})
    assert r.status_code==200,r.text
    fitted=r.json();component=fitted['components'][0]
    assert component['kind']=='spline' and component['fit']['certified_max_deviation_px']<=2
    assert component['original_points']==p['components'][0]['original_points']
    assert snapshot(root)==before
    assert post('cv-proposals/'+p['proposal_id']+'/reject',component_ids=[cid]).status_code==200
    assert snapshot(root)==before

def test_unavailable_disabled_security_and_manual_fallback(env):
    _,app,post,get,root,*_=env;snap=get().json();ref=snap['references'][0]['id'];before=revision(root)
    request={'provider_id':'absent','capability':'detect_edges','reference_id':ref,'view':'side','parameters':{}}
    assert post('cv-jobs',request=request).status_code==503
    request['provider_id']='opencv';request['parameters']['url']='https://example.com/image'
    assert post('cv-jobs',request=request).status_code==422
    request['parameters']={};app.state.registry.config.cv_enabled=False
    assert post('cv-jobs',request=request).status_code==503 and revision(root)==before
    assert post('transactions',commands=[{'type':'MoveObservation','observation_id':'obs_roof_side','pixel':[130,80]}]).status_code==200

def test_cache_keys_cancellation_and_bounded_eviction(env):
    pytest.importorskip('cv2');_,app,post,get,root,*_=env;p=_proposal(env)
    before=revision(root);ref=get().json()['references'][0]['id']
    r=post('cv-jobs',request={'provider_id':'opencv','capability':'detect_wheels','reference_id':ref,'view':'side','parameters':{}})
    job=r.json();assert post('cv-jobs/'+job['job_id']+'/cancel').status_code==200
    for _ in range(200):
        j=get('cv-jobs/'+job['job_id']).json()
        if j['activity']=='FINISHED':break
        time.sleep(.01)
    assert j['result'] in ('CANCELLED','SUCCEEDED') and revision(root)==before
    cache=ByteCache(100,2)
    for i in range(12):cache.put(i,b'x'*45)
    assert cache.bytes<=100 and len(cache.items)<=2 and cache.get(0) is None

def test_accept_invalidates_reviews_edit_reject_do_not_and_undo_restores(env):
    pytest.importorskip('cv2');_,_,post,get,root,*_=env;_source(env,'circle_wheels.png')
    data=get('analysis').json()
    assert post('source-review',decision='ACCEPTED',reviewer='Fixture reviewer',note='Explicit analytical fixture review',expected_subject=data['reviews']['source']['subject']).status_code==200
    data=get('analysis').json()
    cage_result=post('cage-review',decision='ACCEPTED',reviewer='Fixture reviewer',note='Fixture critical coverage checked',expected_subject=data['reviews']['cage']['subject'])
    assert cage_result.status_code==200,cage_result.text
    before=snapshot(root);p=_proposal(env);c=p['components'][0]
    assert get('analysis').json()['reviews']['source']['status']['state']=='READY'
    r=post('cv-proposals/'+p['proposal_id']+'/accept',proposal_revision=p['proposal_revision'],component_ids=[c['id']],semantic_roles={c['id']:'wheel'})
    assert r.status_code==200,r.text
    assert get('analysis').json()['reviews']['source']['status']['state']!='READY'
    assert get('analysis').json()['reviews']['cage']['status']['state']!='READY'
    assert post('undo').status_code==200 and snapshot(root)==before
    assert get('analysis').json()['reviews']['source']['status']['state']=='READY'

def test_cancellation_failure_and_stale_worker_results_are_harmless(env):
    import threading
    _,app,post,get,root,*_=env;began=threading.Event();release=threading.Event()
    class Controlled(CVProvider):
        id='test_local';capabilities=('trace_contour',)
        fail=False
        def metadata(self):return {'provider_id':self.id,'provider_version':'1','available':True,'capabilities':list(self.capabilities),'classification':'local','deterministic':True}
        def run(self,capability,image,parameters,context):
            began.set()
            while not release.wait(.005):context['check']()
            context['check']()
            if self.fail:raise ValueError('Intentional fixture provider failure')
            return {'components':[{'id':'component_0','kind':'polyline','status':'ACTIVE','semantic_role':'UNKNOWN','score':None,'points':[[10,10],[20,20]],'original_points':[[10,10],[20,20]]}],'warnings':[]}
    provider=Controlled();app.state.registry.cv.providers=ProviderRegistry([provider])
    ref=get().json()['references'][0]['id'];request={'provider_id':provider.id,'capability':'trace_contour','reference_id':ref,'view':'side','parameters':{}}
    before=snapshot(root)
    def wait_job(job):
        for _ in range(300):
            value=get('cv-jobs/'+job['job_id']).json()
            if value['activity']=='FINISHED':return value
            time.sleep(.005)
        pytest.fail('Bounded fixture job did not finish')
    job=post('cv-jobs',request=request).json();assert began.wait(2)
    assert post('cv-jobs/'+job['job_id']+'/cancel').status_code==200
    assert wait_job(job)['result']=='CANCELLED' and snapshot(root)==before
    began.clear();release.set();provider.fail=True
    job=post('cv-jobs',request=request).json();assert wait_job(job)['result']=='FAILED' and snapshot(root)==before
    provider.fail=False;release.clear();began.clear()
    job=post('cv-jobs',request=request).json();assert began.wait(2)
    path=root/'project.json';path.write_bytes(path.read_bytes()+b'\n');release.set()
    result=wait_job(job);p=get('cv-proposals/'+result['proposal_id']).json()
    assert result['result']=='SUCCEEDED' and p['status']=='STALE' and result['freshness']=='stale'
    assert post('transactions',commands=[{'type':'MoveObservation','observation_id':'obs_roof_side','pixel':[129,78]}]).status_code==200

def test_cache_reuse_and_parameter_identity(env):
    pytest.importorskip('cv2');_,app,post,get,root,*_=env
    p=_proposal(env);same=_proposal(env);different=_proposal(env,parameters={'min_radius':12})
    assert same['cache_hit'] and p['created_input_hash']==same['created_input_hash']
    assert p['created_input_hash']!=different['created_input_hash']

def test_smart_segments_compose_without_mutation_and_acceptance_is_replayable(env):
    pytest.importorskip('cv2');c,_,post,get,root,ident,h,lease=env
    a=_proposal(env,'strong_edge.png','smart_edge',{'trajectory':[[127,25],[127,110]],'search_radius':8})
    b=_proposal(env,'strong_edge.png','smart_edge',{'trajectory':[[127,110],[127,220]],'search_radius':8})
    before=snapshot(root)
    response=post('cv-traces',proposal_ids=[a['proposal_id'],b['proposal_id']]);assert response.status_code==200,response.text
    p=response.json();assert snapshot(root)==before and len(p['provenance']['segment_input_hashes'])==2
    body={'expected_revision':revision(root),'lease_id':lease,'proposal_revision':p['proposal_revision'],
          'component_ids':['component_0'],'semantic_roles':{'component_0':'roof'},'confirm_observed':True}
    key=uuid.uuid4().hex;headers={**h,'If-Match':body['expected_revision'],'Idempotency-Key':key}
    url=f'/api/v1/projects/{ident}/cv-proposals/{p["proposal_id"]}/accept'
    first=c.post(url,json=body,headers=headers);second=c.post(url,json=body,headers=headers)
    assert first.status_code==second.status_code==200 and first.json()==second.json()
    assert len([o for o in get().json()['observations'] if o['id'].startswith('cv_')])==1

def test_provider_work_has_no_network_requirement(monkeypatch):
    import socket
    def denied(*a,**k):raise AssertionError('CV must not open an external connection')
    monkeypatch.setattr(socket,'create_connection',denied)
    result=_run(OpenCVProvider(),'circle_wheels.png','detect_wheels')
    assert result['components']
