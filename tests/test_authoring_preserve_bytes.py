import json,shutil
from vehiclerecon.core.project import REPOSITORY
from vehiclerecon.authoring.service import AuthoringSession
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.authoring.reviews import subject,review_status

def test_review_does_not_reformat_untouched_canonical_documents(tmp_path):
    root=tmp_path/'study';shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',root)
    cal=root/'generated/calibration.json';cal.write_text(json.dumps(json.loads(cal.read_text()),separators=(',',':'))+'\n')
    before={p:p.read_bytes() for p in (root/'project.json',cal,root/'generated/cage.json')}
    session=AuthoringSession(root);w=Workspace(root)
    result=session.apply([{'type':'SetSourceDisposition','decision':'ACCEPTED','reviewer':'Fixture reviewer','notes':['Analytical fixture'],
                           'expected_subject':subject(w,'source')}],expected_revision=w.revision)
    assert [r['path'] for r in result['changed_files']]==['validation/source_review.json']
    assert all(p.read_bytes()==b for p,b in before.items())
    assert review_status(Workspace(root),'source')['state']=='READY'
    w=Workspace(root)
    session.apply([{'type':'SetCageReview','decision':'ACCEPTED','reviewer':'Fixture reviewer','notes':['Analytical fixture'],
                    'expected_subject':subject(w,'cage')}],expected_revision=w.revision)
    assert review_status(Workspace(root),'cage')['state']=='READY'

def test_only_changed_document_serializes_and_undo_preserves_original_bytes(tmp_path):
    root=tmp_path/'study';shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',root)
    session=AuthoringSession(root);w=Workspace(root);before=dict(w.files)
    result=session.apply([{'type':'MoveWorldLandmark','world_entity_id':'roof_corner','point':[.1,.5,1]}],expected_revision=w.revision)
    assert [f['path'] for f in result['changed_files']]==['generated/cage.json']
    after=Workspace(root)
    assert all(after.files[p]==raw for p,raw in before.items() if p!='generated/cage.json')
    session.undo(expected_revision=session.revision)
    assert Workspace(root).files==before
