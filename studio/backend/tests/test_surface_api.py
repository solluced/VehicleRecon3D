import copy
import shutil
import uuid
import pytest
from fastapi.testclient import TestClient
from vehiclerecon.core.project import REPOSITORY
from vehiclerecon.core.revisions import revision
from vehiclerecon.authoring.service import AuthoringSession
from vehiclerecon_studio.security import Config
from vehiclerecon_studio.app import create_app


@pytest.fixture
def surface(tmp_path):
    path=tmp_path/'surface';shutil.copytree(REPOSITORY/'tests/fixtures/surface_authoring_v2',path)
    config=Config((tmp_path,),9173);secret=config.bootstrap;app=create_app(config)
    with TestClient(app,base_url=config.origin,raise_server_exceptions=False) as client:
        response=client.post('/api/v1/session/bootstrap',json={'secret':secret},headers={'Origin':config.origin})
        headers={'Origin':config.origin,'X-CSRF-Token':response.json()['csrf'],'X-Studio-Tab':uuid.uuid4().hex}
        ident=client.get('/api/v1/projects').json()[0]['id'];base='/api/v1/projects/'+ident
        rev=revision(path);headers['If-Match']=rev
        lease=client.post(base+'/leases',json={'expected_revision':rev},headers=headers).json()['lease_id']
        yield client,app,path,base,headers,lease


def post(surface,suffix,**values):
    c,app,path,base,h,lease=surface;rev=revision(path)
    return c.post(base+'/'+suffix,json={'expected_revision':rev,**values},headers={**h,'If-Match':rev,'Idempotency-Key':uuid.uuid4().hex})


def test_registry_inspect_preview_and_no_raw_execution(surface):
    c,app,path,base,h,lease=surface
    registry=c.get('/api/v1/surface-operations').json()
    assert len(registry['operations'])==13
    context=c.get(base+'/surfaces').json();assert context['evaluation_allowed']
    result=post(surface,'surface-preview',quality='low')
    assert result.status_code==200,result.text
    r=result.json();assert r['status']=='PASS' and len(r['patches'])==2
    assert post(surface,'surface-preview',python='print(1)').status_code==422
    assert c.post(base+'/surface-preview',json={}).status_code==403
    assert c.post(base+'/surface-preview',json={},headers=h).status_code==428
    assert c.get('/api/v1/eval').status_code==404


def test_transient_cycle_validation_and_preview_do_not_write(surface):
    c,app,path,base,h,lease=surface;before=revision(path)
    g=c.get(base+'/surfaces').json()['graph'];n=g['nodes'][-1]
    n['parameters']['left']=n['id'];n['dependencies']=sorted(set(n['parameters'].values()))
    r=post(surface,'surface-validation',graph=g);assert r.status_code==200 and r.json()['validation'][0]['status']=='FAIL'
    assert post(surface,'surface-preview',graph=g).status_code==422
    assert revision(path)==before
    assert post(surface,'surface-preview').json()['status']=='PASS'


def test_api_transactions_use_core_history_and_invalidation(surface):
    c,app,path,base,h,lease=surface;before=(path/'generated/surface_graph.json').read_bytes()
    result=post(surface,'transactions',lease_id=lease,commands=[dict(type='ReverseSurfaceBoundary',node_id='sample.a',boundary='left')])
    assert result.status_code==200,result.text
    assert 'surfaces' in result.json()['stale']['stages'] and 'delivery' in result.json()['stale']['stages']
    assert post(surface,'surface-preview').json()['status']=='FAIL'
    assert post(surface,'undo',lease_id=lease).status_code==200
    assert (path/'generated/surface_graph.json').read_bytes()==before
    assert post(surface,'surface-preview').json()['status']=='PASS'


@pytest.mark.parametrize('scope',['source','cage'])
def test_cached_preview_still_requires_current_reviews(surface,scope):
    c,app,path,base,h,lease=surface;assert post(surface,'surface-preview').json()['status']=='PASS'
    s=AuthoringSession(path)
    command=dict(type='MoveWorldLandmark',world_entity_id='roof_corner',point=[0,.5,1.1]) if scope=='cage' else dict(type='MoveObservation',observation_id='obs_roof_side',pixel=[129,78])
    s.apply([command],expected_revision=s.revision)
    assert c.get(base+'/surfaces').json()['gate']=='BLOCKED BY SOURCE/CAGE ACCEPTANCE'
    assert post(surface,'surface-preview').status_code==422


def test_incomplete_draft_persists_safely(surface):
    c,app,path,base,h,lease=surface
    r=post(surface,'transactions',lease_id=lease,commands=[dict(type='AddSurfacePatch',patch_id='draft.panel',node_id='draft.sample',name='Draft',semantic_role='panel',op='coons')])
    assert r.status_code==200,r.text
    context=c.get(base+'/surfaces').json();assert context['validation'][-1]['status']=='INCOMPLETE'
    r=post(surface,'surface-preview').json();assert not r['certified_current'] and r['patches']==[]
