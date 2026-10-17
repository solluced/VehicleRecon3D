import copy
import hashlib
import io
import json
import shutil
import threading
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from vehiclerecon.core.project import REPOSITORY
from vehiclerecon.core.locking import ProjectLock
from vehiclerecon.core.revisions import revision
from vehiclerecon_studio.security import Config
from vehiclerecon_studio.app import create_app
from vehiclerecon_studio.events import EventBus


@pytest.fixture
def env(tmp_path):
    shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',tmp_path/'study')
    config=Config((tmp_path,),9173);secret=config.bootstrap;app=create_app(config)
    client=TestClient(app,base_url=config.origin,raise_server_exceptions=False)
    response=client.post('/api/v1/session/bootstrap',json={'secret':secret},headers={'Origin':config.origin})
    assert response.status_code==200,response.text
    headers={'Origin':config.origin,'X-CSRF-Token':response.json()['csrf'],'X-Studio-Tab':uuid.uuid4().hex}
    ident=client.get('/api/v1/projects').json()[0]['id'];snap=client.get('/api/v1/projects/'+ident,headers=headers).json()
    headers['If-Match']=snap['revision']
    lease=client.post(f'/api/v1/projects/{ident}/leases',json={'expected_revision':snap['revision']},headers=headers).json()['lease_id']
    return client,app,headers,ident,lease,tmp_path,secret


def post(env,operation,**fields):
    client,app,headers,ident,lease,root,_=env
    rev=revision(root/'study');h={**headers,'If-Match':rev,'Idempotency-Key':uuid.uuid4().hex}
    return client.post(f'/api/v1/projects/{ident}/{operation}',json={'expected_revision':rev,'lease_id':lease,**fields},headers=h)


@pytest.mark.parametrize('host',['evil.test','localhost:9173','127.0.0.1:9999'])
def test_host_rejected(env,host):
    assert env[0].get('/api/v1/projects',headers={'Host':host}).status_code==403


@pytest.mark.parametrize('origin',['https://evil.test','null','http://localhost:9173'])
def test_origin_rejected(env,origin):assert env[0].get('/api/v1/projects',headers={'Origin':origin}).status_code==403


def test_bootstrap_single_use_and_session_protected(env):
    c,app,h,ident,lease,root,secret=env
    assert c.post('/api/v1/session/bootstrap',json={'secret':secret},headers={'Origin':h['Origin']}).status_code==401
    c.cookies.clear();assert c.get('/api/v1/projects').status_code==401
    assert c.get('/openapi.json').status_code==404


def test_csrf_origin_and_revision_required(env):
    c,app,h,ident,lease,root,_=env;url=f'/api/v1/projects/{ident}/undo'
    assert c.post(url,json={}).status_code==403
    assert c.post(url,json={},headers={'Origin':h['Origin']}).status_code==403
    assert c.post(url,json={},headers=h).status_code==428


def test_v2_typed_edit_undo_redo_idempotent_and_stale(env):
    c,app,h,ident,lease,root,_=env;before=revision(root/'study')
    response=post(env,'transactions',commands=[{'type':'MoveObservation','observation_id':'obs_roof_side','pixel':[129,78]}])
    assert response.status_code==200,response.text
    after=response.json()['revision'];assert after!=before
    assert post(env,'undo').json()['revision']==before
    assert post(env,'redo').json()['revision']==after
    stale=c.post(f'/api/v1/projects/{ident}/transactions',json={'expected_revision':before,'lease_id':lease,'commands':[]},headers={**h,'If-Match':before,'Idempotency-Key':uuid.uuid4().hex})
    assert stale.status_code==409
    body={'expected_revision':after,'lease_id':lease,'commands':[{'type':'MoveObservation','observation_id':'obs_roof_side','pixel':[130,78]}]}
    headers={**h,'If-Match':after,'Idempotency-Key':uuid.uuid4().hex};url=f'/api/v1/projects/{ident}/transactions'
    first=c.post(url,json=body,headers=headers);retry=c.post(url,json=body,headers=headers)
    assert first.status_code==200 and retry.json()==first.json()
    body['commands'][0]['pixel']=[131,78]
    assert c.post(url,json=body,headers=headers).status_code==409


def test_invalid_shell_raw_patch_and_gate_commands_not_available(env):
    for command in ({'type':'Patch','path':'project.json'},{'type':'SetSourceDisposition','decision':'ACCEPTED'},
                    {'type':'AddSplinePoint','target':'cage'},{'type':'MoveObservation','observation_id':'obs_roof_side','pixel':[0,0],'shell':'whoami'}):
        before=revision(env[5]/'study')
        assert post(env,'transactions',commands=[command]).status_code==422
        assert revision(env[5]/'study')==before
    for url in ['/api/v1/shell','/api/v1/file?path=project.json','/api/v1/run']:
        assert env[0].get(url).status_code==404


@pytest.mark.parametrize('ident',['..','C:%5CWindows','%2e%2e%2fsecret','not_registered'])
def test_traversal_and_unknown_registry_id(env,ident):assert env[0].get('/api/v1/projects/'+ident,headers=env[2]).status_code in (403,404,422)


def test_two_tab_lease_and_core_lock_conflict(env):
    c,app,h,ident,lease,root,_=env
    r=c.post(f'/api/v1/projects/{ident}/leases',json={'expected_revision':revision(root/'study')},headers={**h,'X-Studio-Tab':uuid.uuid4().hex})
    assert r.status_code==423
    with ProjectLock(root/'study','test-held-lock'):
        # HTTP handlers run on another thread, so cannot reuse this owner.
        assert post(env,'transactions',commands=[{'type':'MoveObservation','observation_id':'obs_roof_side','pixel':[1,2]}]).status_code==423


def test_external_edit_does_not_overwrite_and_reload(env):
    c,app,h,ident,lease,root,_=env;before=revision(root/'study')
    path=root/'study/project.json';path.write_bytes(path.read_bytes()+b'\n')
    response=c.post(f'/api/v1/projects/{ident}/undo',json={'expected_revision':before,'lease_id':lease},headers={**h,'Idempotency-Key':uuid.uuid4().hex})
    assert response.status_code==409
    assert post(env,'reload').json()['snapshot']['revision']==revision(root/'study')


def test_import_4k_exact_bytes_and_canonical_reopen(env):
    c,app,h,ident,lease,root,_=env
    roots=c.get('/api/v1/roots').json()[0]
    response=c.post('/api/v1/projects',json={'name':'New_Study','profile':'sedan','root_id':roots['id'],'expected_revision':roots['revision'],'dimensions':{'length_m':None}},headers={**h,'If-Match':roots['revision'],'Idempotency-Key':uuid.uuid4().hex})
    assert response.status_code==200,response.text
    snap=response.json();pid=snap['id'];rev=snap['revision']
    lid=c.post(f'/api/v1/projects/{pid}/leases',json={'expected_revision':rev},headers={**h,'If-Match':rev}).json()['lease_id']
    data=io.BytesIO();Image.new('RGB',(3840,2160),(30,40,50)).save(data,format='PNG');raw=data.getvalue()
    r=c.post(f'/api/v1/projects/{pid}/reference-imports',content=raw,headers={**h,'Content-Type':'application/octet-stream','If-Match':rev,'X-Expected-Revision':rev,'X-Editor-Lease':lid,'Idempotency-Key':uuid.uuid4().hex})
    assert r.status_code==200,r.text
    snap=r.json()['snapshot'];ref=snap['references'][0]
    assert snap['project']['dimensions']['length_m'] is None and ref['size']==[3840,2160]
    assert c.get(f'/api/v1/projects/{pid}/references/{ref["id"]}/image').content==raw
    assert ref['sha256']==hashlib.sha256(raw).hexdigest()
    assert revision(root/'new_study')==r.json()['revision']
    reopened=create_app(Config((root,),9174)).state.registry
    reopened_id=next(k for k,v in reopened.projects.items() if v.name=='new_study')
    assert reopened.snapshot(reopened_id)['revision']==snap['revision']


def test_upload_limits_and_invalid_images(env):
    c,app,h,ident,lease,root,_=env;app.state.config.max_upload=8
    r=c.post(f'/api/v1/projects/{ident}/reference-imports',content=b'0123456789',headers=h)
    assert r.status_code==413
    app.state.config.max_upload=64*1024*1024
    r=c.post(f'/api/v1/projects/{ident}/reference-imports',content=b'<svg onload=alert(1)>',headers=h)
    assert r.status_code==422


def test_read_only_v1_and_safe_roots(env):
    c,app,h,ident,lease,root,_=env;legacy=root/'legacy';legacy.mkdir()
    shutil.copyfile(REPOSITORY/'projects/tesla/project.json',legacy/'project.json')
    for folder in ('input','generated'):shutil.copytree(REPOSITORY/'projects/tesla'/folder,legacy/folder)
    items=c.get('/api/v1/projects').json();old=next(p for p in items if p.get('version')==1)
    assert old['read_only']
    assert c.post(f'/api/v1/projects/{old["id"]}/leases',json={'expected_revision':old['revision']},headers={**h,'If-Match':old['revision']}).status_code==403
    roots=c.get('/api/v1/roots').json()[0]
    for name in ('../escape','CON','A/B','C:\\a'):
        assert c.post('/api/v1/projects',json={'name':name,'root_id':roots['id'],'expected_revision':roots['revision']},headers={**h,'If-Match':roots['revision']}).status_code==422
    assert c.post('/api/v1/projects',json={'name':'Okay','root_id':'outside','expected_revision':roots['revision']},headers={**h,'If-Match':roots['revision']}).status_code==404


def test_ui_state_not_canonical_and_geometry_rejected(env):
    before=revision(env[5]/'study')
    assert post(env,'preferences',preferences={'active_view':'top','layers':{'image':{'visible':False,'opacity':.5}}}).status_code==200
    assert revision(env[5]/'study')==before
    assert post(env,'preferences',preferences={'observations':[]}).status_code==422


def test_sse_epoch_and_expired_cursor_resync():
    bus=EventBus(limit=2);first=bus.emit('project_changed');bus.emit('validation_changed');bus.emit('revision_changed')
    assert bus.replay(first['id'])[0]['kind']=='resync'
    current=bus.records[0];assert bus.replay(current['id'])[0]['kind']=='revision_changed'
    assert EventBus().replay(current['id'])[0]['kind']=='resync'


def test_loopback_binding_only(tmp_path):
    for host in ('0.0.0.0','::','localhost'):
        with pytest.raises(ValueError):Config((tmp_path,),9173,host=host)
