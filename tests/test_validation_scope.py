import copy,json,shutil
import pytest
from vehiclerecon.core.project import REPOSITORY,validate,full_validation
from vehiclerecon.core.errors import SchemaError,ReconError
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.authoring.service import AuthoringSession

def test_structural_memo_and_full_audit_reject_the_same_mutations():
    cal=json.loads((REPOSITORY/'tests/fixtures/authoring_v2/generated/calibration.json').read_text())
    validate(cal,'calibration')
    cases=[cal]
    for op in ('unknown','pixel','nonfinite','duplicate','bad_kind'):
        c=copy.deepcopy(cal);o=c['views']['side']['landmarks']['observations'][0]
        if op=='unknown':o['unknown']=1
        if op=='pixel':o['pixel']=[1]
        if op=='nonfinite':o['pixel'][0]=float('nan')
        if op=='duplicate':o['pixel']=tuple(o['pixel'])
        if op=='bad_kind':o['kind']='bad'
        cases.append(c)
    for c in cases:
        results=[]
        for audit in (False,True):
            try:validate(c,'calibration',full=audit);results.append(True)
            except SchemaError:results.append(False)
        assert results[0]==results[1]

def test_cross_document_semantics_never_uses_structural_cache_as_authority(tmp_path):
    shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',tmp_path/'study');w=Workspace(tmp_path/'study')
    files=copy.deepcopy(w.files);cal=copy.deepcopy(w.documents['calibration'])
    cal['correspondences'][0]['observation_revision']+=10
    files[w.project.data['generated']['calibration']]=(json.dumps(cal)+'\n').encode()
    for audit in (False,True):
        with pytest.raises(ReconError):
            if audit:
                with full_validation():w.validate(files)
            else:w.validate(files)

def test_incremental_and_full_transactions_are_byte_identical(tmp_path):
    for name in ('fast','audit'):shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',tmp_path/name)
    a,b=AuthoringSession(tmp_path/'fast'),AuthoringSession(tmp_path/'audit')
    for pixel in ([129,78],[130,79],[128,78]):
        cmd=[{'type':'MoveObservation','observation_id':'obs_roof_side','pixel':pixel}]
        x=a.apply(cmd,expected_revision=a.revision)
        with full_validation():y=b.apply(cmd,expected_revision=b.revision)
        assert {k:v for k,v in x.items() if k!='transaction_id'}=={k:v for k,v in y.items() if k!='transaction_id'}
        assert Workspace(a.root).files==Workspace(b.root).files
