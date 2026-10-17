import copy
import json
import shutil
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from vehiclerecon.core.project import REPOSITORY
from vehiclerecon.core.revisions import revision
from vehiclerecon_studio.security import Config
from vehiclerecon_studio.app import create_app
from vehiclerecon_studio.retention import Responses


@pytest.fixture
def env(tmp_path):
    shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',tmp_path/'study')
    config=Config((tmp_path,),9173);app=create_app(config);c=TestClient(app,base_url=config.origin)
    token=c.post('/api/v1/session/bootstrap',json={'secret':config.bootstrap},headers={'Origin':config.origin}).json()
    h={'Origin':config.origin,'X-CSRF-Token':token['csrf'],'X-Studio-Tab':uuid.uuid4().hex}
    ident=c.get('/api/v1/projects').json()[0]['id'];rev=revision(tmp_path/'study')
    lease=c.post(f'/api/v1/projects/{ident}/leases',json={'expected_revision':rev},headers={**h,'If-Match':rev}).json()['lease_id']
    def post(op,**fields):
        rev=revision(tmp_path/'study')
        return c.post(f'/api/v1/projects/{ident}/{op}',json={'expected_revision':rev,'lease_id':lease,**fields},headers={**h,'If-Match':rev,'Idempotency-Key':uuid.uuid4().hex})
    def analysis():return c.get(f'/api/v1/projects/{ident}/analysis').json()
    return c,app,post,analysis,tmp_path/'study'


def test_observation_and_world_moves_are_distinct_and_undoable(env):
    _,_,post,analysis,_=env;before=analysis()
    assert post('transactions',commands=[{'type':'MoveObservation','observation_id':'obs_roof_side','pixel':[132,78]}]).status_code==200
    moved=analysis();assert moved['world_landmarks']==before['world_landmarks']
    assert moved['residuals']['rows'][0]['heat']=='FAIL'
    assert post('transactions',commands=[{'type':'MoveWorldLandmark','world_entity_id':'roof_corner','point':[.1,.6,1.1]}]).status_code==200
    world=analysis();assert all(a['projected_pixel']!=b['projected_pixel'] for a,b in zip(moved['residuals']['rows'],world['residuals']['rows']))
    assert post('undo').status_code==200
    assert analysis()['world_landmarks']==before['world_landmarks']


def test_fit_is_proposal_until_one_undoable_apply_and_stales_on_external_change(env):
    _,_,post,analysis,root=env;before=revision(root)
    r=post('fit-proposals',request={'world_entity_id':'roof_corner','observation_ids':['obs_roof_side','obs_roof_top']})
    assert r.status_code==200,r.text
    fit=r.json();assert revision(root)==before and fit['proposal_only']
    assert fit['proposed_xyz']==pytest.approx([0,.5,1])
    assert post('apply-fit',proposal_id=fit['proposal_id']).status_code==200
    path=root/'project.json';path.write_bytes(path.read_bytes()+b'\n')
    assert post('apply-fit',proposal_id=fit['proposal_id']).status_code==409


def test_unbound_plane_creation_requires_explicit_depth(env):
    _,_,post,analysis,root=env
    request={'world_entity_id':'new_point','placement':{'view':'side','pixel':[128,78],'normal':[0,1,0],'offset':.7}}
    r=post('fit-proposals',request=request);assert r.status_code==200
    assert 'new_point' not in analysis()['world_landmarks']
    assert post('apply-fit',proposal_id=r.json()['proposal_id']).status_code==200
    assert analysis()['world_landmarks']['new_point']==pytest.approx([0,.7,1])
    request['placement']['normal']=[0,0,1]
    assert post('fit-proposals',request=request).status_code==422


def test_review_requires_inspected_subject_person_note_and_rejection_blocks_surfaces(env):
    _,_,post,analysis,root=env;data=analysis()
    assert post('source-review',decision='ACCEPTED',reviewer='',note='review',expected_subject=data['reviews']['source']['subject']).status_code==422
    assert post('source-review',decision='ACCEPTED',reviewer='Human',note='Fixture inspected',expected_subject='0'*64).status_code==409
    assert post('source-review',decision='ACCEPTED',reviewer='Human',note='Fixture inspected',expected_subject=data['reviews']['source']['subject']).status_code==200
    data=analysis()
    assert post('cage-review',decision='ACCEPTED',reviewer='Human',note='All four critical rows inspected',expected_subject=data['reviews']['cage']['subject']).status_code==200
    assert analysis()['reviews']['cage']['status']['state']=='READY'
    data=analysis()
    assert post('source-review',decision='INCONSISTENT_SOURCE',reviewer='Human',note='Demonstrate explicit rejection',expected_subject=data['reviews']['source']['subject']).status_code==200
    from vehiclerecon.authoring.readiness import readiness
    assert readiness(root)['surfaces']['state']=='BLOCKED'
    assert analysis()['reviews']['source']['status']['decision']=='INCONSISTENT_SOURCE'
    assert post('undo').status_code==200
    assert analysis()['reviews']['source']['status']['decision']=='ACCEPTED'


def test_binding_and_policy_edits_are_core_commands(env):
    _,_,post,analysis,_=env;data=analysis();link=copy.deepcopy(data['correspondences'][0])
    policy=copy.deepcopy(data['policy']);policy['critical_correspondence_ids'].remove(link['id'])
    assert post('transactions',commands=[{'type':'SetCoveragePolicy','policy':policy},{'type':'UnbindObservation','correspondence_id':link['id']}]).status_code==200
    assert len(analysis()['correspondences'])==3
    assert post('transactions',commands=[{'type':'BindObservation','correspondence':link}]).status_code==200
    assert len(analysis()['correspondences'])==4


def test_responses_are_byte_bounded_and_keep_identical_replay_value():
    cache=Responses(limit=3,byte_limit=1000);value=('fingerprint',{'data':'x'*250})
    cache['a']=value;assert cache.get('a') is value
    for i in range(8):cache[str(i)]=('f',{'data':'x'*250})
    assert len(cache)<=3 and cache.retained_bytes<=1000 and cache.get('a') is None


def test_json_response_preserves_validated_unicode_snapshot_and_events(env):
    c,app,post,analysis,root=env
    response=post('transactions',commands=[{'type':'SetObservationProperties','observation_id':'obs_roof_side','values':{'provenance':{'type':'measured','method':'Ручная проверка'}}}])
    assert response.status_code==200 and response.json()['snapshot']['observations'][0]['provenance']['method']=='Ручная проверка'
    assert {e['kind'] for e in app.state.registry.bus.records}>={'residuals_changed','source_review_changed','cage_review_changed'}


def test_legacy_mark2_diagnostics_are_current_and_read_only():
    config=Config((REPOSITORY/'projects',),9173);app=create_app(config);registry=app.state.registry
    ident=next(k for k,p in registry.projects.items() if p.name=='mark2')
    before=revision(registry.resolve(ident));data=registry.analysis(ident)
    assert data['read_only'] and data['legacy_evidence_current']
    assert data['source_condition']=='INCONSISTENT_SOURCE' and len(data['residuals']['rows'])==66
    assert any(r['heat']=='FAIL' and 'pillar' in r['semantic_role'] for r in data['residuals']['rows'])
    assert data['legacy_summary']['greenhouse_by_view']['front']==pytest.approx(1,abs=.001)
    assert data['legacy_summary']['greenhouse_by_view']['rear']==pytest.approx(4,abs=.01)
    assert revision(registry.resolve(ident))==before
