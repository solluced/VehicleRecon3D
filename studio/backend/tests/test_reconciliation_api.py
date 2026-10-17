import copy,json,sys,uuid
from pathlib import Path
import pytest
from concurrent.futures import ThreadPoolExecutor
import io
from PIL import Image
from fastapi.testclient import TestClient
from vehiclerecon.core.project import REPOSITORY
from vehiclerecon.core.revisions import revision,snapshot
from vehiclerecon.core.manifest import digest_file
from vehiclerecon_studio.security import Config
from vehiclerecon_studio.app import create_app
sys.path.insert(0,str(REPOSITORY/'tests'))
from reconciliation_fixture import prepare

@pytest.fixture
def study(tmp_path):
    root=tmp_path/'study';request=prepare(root);config=Config((tmp_path,),9173);app=create_app(config)
    with TestClient(app,base_url=config.origin) as c:
        auth=c.post('/api/v1/session/bootstrap',json={'secret':config.bootstrap},headers={'Origin':config.origin}).json()
        h={'Origin':config.origin,'X-CSRF-Token':auth['csrf'],'X-Studio-Tab':uuid.uuid4().hex}
        ident=c.get('/api/v1/projects').json()[0]['id'];base='/api/v1/projects/'+ident;rev=revision(root)
        lease=c.post(base+'/leases',json={'expected_revision':rev},headers={**h,'If-Match':rev}).json()['lease_id']
        def post(op,**body):
            rev=revision(root);body.setdefault('expected_revision',rev)
            return c.post(base+'/'+op,json=body,headers={**h,'If-Match':rev,'Idempotency-Key':uuid.uuid4().hex})
        yield c,app,root,request,base,h,lease,post

def test_noncanonical_candidate_generation_preview_reject_and_comparison(study):
    c,app,root,req,base,h,lease,post=study;before=snapshot(root)
    for creator in ('A','B'):
        r=post('reconciliation',request=req,creator=creator);assert r.status_code==200,r.text
        p=r.json();assert p['report']['eligible'] and p['status']=='ELIGIBLE_FOR_ACTIVATION'
    assert snapshot(root)==before
    context=c.get(base+'/reconciliation?view=top',headers=h).json();assert len(context['candidates'])==2
    def fetch(kind):return c.get(base+f'/reconciliation/{p["id"]}/preview/{kind}',headers=h)
    with ThreadPoolExecutor(max_workers=3) as pool:previews=list(pool.map(fetch,('raw','rectified','difference')))
    for r in previews:
        assert r.status_code==200 and r.content.startswith(b'\x89PNG')
        with Image.open(io.BytesIO(r.content)) as image:image.verify()
    r=c.post(base+f'/reconciliation/{p["id"]}/reject',json={'candidate_revision':p['revision'],'reason':'Independent inspection rejection'},headers=h)
    assert r.status_code==200 and r.json()['status']=='REJECTED'
    assert not r.json()['report']['eligible'] and 'Rejected: Independent inspection rejection' in r.json()['report']['reasons']
    assert snapshot(root)==before

def test_activation_stales_reviews_never_autoaccepts_and_exact_undo(study):
    c,app,root,req,base,h,lease,post=study
    for kind in ('source','cage'):
        subject=c.get(base+'/analysis',headers=h).json()['reviews'][kind]['subject']
        r=post(kind+'-review',lease_id=lease,decision='NEEDS_CORRECTION',reviewer='Fixture reviewer',note='Inspect prior evidence',expected_subject=subject)
        assert r.status_code==200,r.text
    p=post('reconciliation',request=req,creator='Reviewer').json();before=snapshot(root)
    r=post('activate-rectification',lease_id=lease,candidate_id=p['id'],candidate_revision=p['revision'],confirm_activation=True,response_format='delta')
    assert r.status_code==200,r.text
    assert 'snapshot_delta' in r.json()
    analysis=c.get(base+'/analysis',headers=h).json()
    assert not analysis['reviews']['source']['status']['current'] and not analysis['reviews']['cage']['status']['current']
    assert analysis['reviews']['source']['status']['decision']=='NEEDS_CORRECTION'
    assert c.get(base+'/reconciliation/'+p['id'],headers=h).json()['active']
    assert post('undo',lease_id=lease).status_code==200 and snapshot(root)==before
    assert not c.get(base+'/reconciliation/'+p['id'],headers=h).json()['active']
    assert (root/'.studio/rectification'/f'{p["id"]}.json').is_file()

def test_stale_candidate_fence_and_security(study):
    c,app,root,req,base,h,lease,post=study
    p=post('reconciliation',request=req,creator='Author').json()
    path=root/'generated/calibration.json';path.write_bytes(path.read_bytes()+b'\n')
    assert c.get(base+'/reconciliation/'+p['id'],headers=h).json()['status']=='STALE'
    r=post('activate-rectification',lease_id=lease,candidate_id=p['id'],candidate_revision=p['revision'],confirm_activation=True)
    assert r.status_code==409,r.text
    bad={**req,'url':'https://example.com'};assert post('reconciliation',request=bad,creator='Author').status_code==422
    assert c.get(base+'/reconciliation/../../../project.json',headers=h).status_code!=200

def test_source_replacement_preserves_bytes_and_world_and_stales_candidates(study):
    c,app,root,req,base,h,lease,post=study
    p=post('reconciliation',request=req,creator='Author').json();before=snapshot(root)
    old=(root/'input/reference.png').read_bytes();world=(root/'generated/cage.json').read_bytes()
    # Valid original PNG with harmless distinct trailing bytes; no source mutation.
    raw=old+b'\nreplacement-v04\n';rev=revision(root)
    r=c.post(base+'/reference-imports',content=raw,headers={**h,'Content-Type':'application/octet-stream','If-Match':rev,
        'X-Expected-Revision':rev,'X-Editor-Lease':lease,'X-Replacement-View':'top','X-Confirm-Replacement':'true','Idempotency-Key':uuid.uuid4().hex})
    assert r.status_code==200,r.text
    data=r.json();assert (root/'input/reference.png').read_bytes()==old and (root/'generated/cage.json').read_bytes()==world
    cal=json.loads((root/'generated/calibration.json').read_text());assert cal['views']['top']['source_state']=='CALIBRATION_REQUIRED'
    assert cal['views']['top']['landmarks']['observations']==json.loads(before['generated/calibration.json'])['views']['top']['landmarks']['observations']
    assert not cal['authoring_policy']['coverage_confirmed']
    assert c.get(base+'/reconciliation/'+p['id'],headers=h).json()['status']=='STALE'
    assert data['snapshot']['readiness']['calibration']['state']=='BLOCKED'
    assert post('undo',lease_id=lease).status_code==200 and snapshot(root)==before
