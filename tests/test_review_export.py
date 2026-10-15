from pathlib import Path
import shutil
import pytest
from vehiclerecon.core.project import Project,REPOSITORY
from vehiclerecon.core.errors import BlockedError,GateError
from vehiclerecon.core.manifest import digest_file
from vehiclerecon.validation.report import review,record_review
from vehiclerecon.export.verify import GLB
from vehiclerecon.export.fbx import export as fbx
from vehiclerecon.viewer.builder import embedded_bytes

@pytest.fixture
def project(tmp_path):
    source=REPOSITORY/'projects/tesla'
    for folder in ['input','generated']:
        shutil.copytree(source/folder,tmp_path/folder)
    shutil.copyfile(source/'project.json',tmp_path/'project.json')
    p=Project(tmp_path)
    for relative in ['validation/geometry_audit.json',*p.data['presentation']['review_proofs']]:
        target=p.path(relative);target.parent.mkdir(exist_ok=True);shutil.copyfile(source/relative,target)
    return p

def test_missing_review_blocks(project):
    with pytest.raises(BlockedError):review(project,'0'*64)

def test_explicit_review_and_staleness(project):
    record=record_review(project,reviewer='test reviewer',decision='PASS',notes=['Explicit test decision'],limitations=[])
    assert review(project,record['geometry_hash'])['reviewer']=='test reviewer'
    with pytest.raises(BlockedError):review(project,'0'*64)
    proof=project.path(next(iter(record['proof_hashes'])))
    proof.write_bytes(b'changed')
    with pytest.raises(BlockedError):review(project,record['geometry_hash'])

def test_failed_review_gate(project):
    record=record_review(project,reviewer='test reviewer',decision='FAIL',notes=['Reject'],limitations=[])
    with pytest.raises(GateError):review(project,record['geometry_hash'])

def test_config_staleness(project):
    record=record_review(project,reviewer='test reviewer',decision='PASS',notes=['Accept test'],limitations=[])
    project.data['presentation']['samples']+=1
    with pytest.raises(BlockedError):review(project,record['geometry_hash'])

def test_fbx_is_not_faked(project):
    with pytest.raises(BlockedError):fbx(project)

def test_glb_fixture_geometry():
    path=REPOSITORY/'tests/fixtures/tesla/baseline/delivered/exports/tesla_surface_model.glb'
    model=GLB(path);geometry=model.geometry()
    assert len(geometry)==191
    assert sum(o['triangles'] for o in geometry.values())==245952

def test_corrupt_glb(tmp_path):
    path=tmp_path/'bad.glb';path.write_bytes(b'invalid')
    with pytest.raises(GateError):GLB(path)

def test_corrupt_accessor():
    model=GLB(REPOSITORY/'tests/fixtures/tesla/baseline/delivered/exports/tesla_surface_model.glb')
    accessor=model.data['accessors'][0]
    model.data['bufferViews'][accessor['bufferView']]['byteLength']=0
    with pytest.raises(GateError):model.accessor(0)

def test_exact_viewer_bytes():
    p=Project(REPOSITORY/'projects/tesla')
    assert embedded_bytes(p.path('output/viewer.html').read_text())==p.glb.read_bytes()
    with pytest.raises(GateError):embedded_bytes('no model')
