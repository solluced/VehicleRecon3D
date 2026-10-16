"""Headless policy gates and preserved rejected-source evidence."""
import copy
import json
import shutil
import pytest
from vehiclerecon.core.project import Project, REPOSITORY
from vehiclerecon.core.pipeline import Pipeline, Status
from vehiclerecon.core.errors import BlockedError, ReferenceError
from vehiclerecon.core.manifest import digest_file
from vehiclerecon.authoring.service import AuthoringSession
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.authoring.projection import residual_report
from vehiclerecon.reference.rectification import AxisRectification


@pytest.fixture
def root(tmp_path):
    shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',tmp_path,dirs_exist_ok=True)
    return tmp_path


@pytest.mark.parametrize('change',['missing_source','missing_cage','stale_source','stale_cage'])
def test_acceptance_precedes_cache_lookup_and_direct_execution(root,change,monkeypatch):
    if change.startswith('missing'):
        (root/('validation/'+change.split('_')[1]+'_review.json')).unlink()
    else:
        path=root/('generated/calibration.json' if change=='stale_source' else 'generated/cage.json')
        path.write_bytes(path.read_bytes()+b'\n')
    pipeline=Pipeline(Project(root))
    looked_up=[]
    class Cache:
        def key(self,stage,*args):return stage
        def hit(self,stage,key):
            looked_up.append(stage)
            return {'outputs':[],'result_key':stage}
        def store(self,*args,**kwargs):return {'result_key':args[0]}
    pipeline.cache=Cache()
    monkeypatch.setattr('vehiclerecon.core.cache.input_slice',lambda *args:{})
    monkeypatch.setattr(pipeline,'execute',lambda stage:[])
    assert pipeline.run(until='surfaces')==1
    assert pipeline.results[-1].status==Status.BLOCKED
    assert 'surfaces' not in looked_up
    with pytest.raises(BlockedError):Pipeline(Project(root),use_cache=False).execute('surfaces')


def test_single_failed_residual_cannot_be_averaged_into_acceptance(root):
    w=Workspace(root);cal=copy.deepcopy(w.documents['calibration'])
    cal['views']['side']['landmarks']['observations'][0]['pixel'][0]+=3
    report=residual_report(cal,w.documents['cage'])
    assert report['summary']['mean_residual_px']<2
    assert report['status']=='FAIL' and report['summary']['passed']==3


def test_extreme_active_warp_rejected_atomically(root):
    session=AuthoringSession(root);before=session.revision
    view=copy.deepcopy(Workspace(root).documents['calibration']['views']['top'])
    view.pop('landmarks',None);view.pop('source_curves',None)
    rejected=json.loads((REPOSITORY/'projects/mark2/validation/rectification_candidate.json').read_text())
    view['rectification']=rejected['rectification']
    with pytest.raises(ReferenceError,match='local scale'):
        session.apply([{'type':'SetCalibrationView','view':'top','data':view}],expected_revision=before)
    assert session.revision==before


def test_mark2_rejected_candidate_remains_inactive():
    root=REPOSITORY/'projects/mark2'
    report=json.loads((root/'validation/reference_reconciliation_report.json').read_text())
    assert report['status']=='REFERENCE_SOURCE_INCONSISTENT'
    for relative,sha in report['protected_artifact_sha256'].items():
        assert digest_file(root/relative)==sha,relative
    candidate=json.loads((root/'validation/rectification_candidate.json').read_text())
    assert candidate['status']=='REJECTED_NOT_ACTIVE'
    with pytest.raises(ReferenceError,match='local scale'):AxisRectification(candidate['rectification'])
    assert not (root/'.cache/surfaces.blend').exists()
    assert not (root/'.cache/details.blend').exists()
