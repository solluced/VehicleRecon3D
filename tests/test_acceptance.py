import hashlib,json
from pathlib import Path
import pytest
from vehiclerecon.core.project import Project,REPOSITORY,read_json
from vehiclerecon.core.manifest import digest_file
from vehiclerecon.core.errors import GateError
from vehiclerecon.validation.geometry import validate_roles
from vehiclerecon.validation.regression import compare_sources
from vehiclerecon.viewer.builder import embedded_bytes
from vehiclerecon.core.delivery import verify_manifest

def test_frozen_baseline_integrity():
    base=REPOSITORY/'tests/fixtures/tesla/baseline'
    for line in (base/'MANIFEST.sha256').read_text().splitlines():
        expected,path=line.split(None,1)
        assert digest_file(base/path)==expected,path

def test_legacy_source_fixture_integrity():
    base=REPOSITORY/'tests/fixtures/tesla/legacy_source'
    for line in (base/'MANIFEST.sha256').read_text().splitlines():
        expected,path=line.split(None,1)
        assert digest_file(base/path)==expected,path

def test_semantic_roles():
    profile={'roles':['hood'],'optional_roles':['hatch']}
    assert validate_roles(profile,{'hood':['surface']},{'surface'})['pass']
    assert not validate_roles(profile,{},set())['pass']
    assert not validate_roles(profile,{'hood':['missing']},{'surface'})['pass']

def test_threshold_floors_are_frozen():
    p=Project(REPOSITORY/'projects/tesla')
    baseline=read_json(REPOSITORY/'tests/fixtures/tesla/baseline/comparison.json')['views']
    for view,record in baseline.items():
        assert p.data['validation']['thresholds'][view]>=record['minimum']
        assert p.data['validation']['baseline_iou'][view]==record['delivered_iou']

@pytest.mark.integration
def test_current_tesla_regression_artifacts():
    p=Project(REPOSITORY/'projects/tesla')
    masks=read_json(p.path('validation/final_migration_report.json'))
    for view,baseline in p.data['validation']['baseline_iou'].items():
        assert masks['views'][view]['iou']>=p.data['validation']['thresholds'][view]
        assert masks['views'][view]['iou']>=baseline-p.data['validation']['max_iou_regression']
    audit=read_json(p.path('validation/geometry_audit.json'))
    assert audit['status']=='PASS' and audit['audit_mutated_geometry'] is False
    assert audit['semantic_roles_pass'] and audit['metric_units']
    current=read_json(p.path('output/export_manifest.json'))
    old=read_json(REPOSITORY/'tests/fixtures/tesla/baseline/delivered/exports/export_manifest.json')
    overlays={p.data['presentation']['wire']['prefix']+n for n in p.data['presentation']['wire_sources']}
    assert compare_sources(old['source_geometry'],current['source_geometry'],overlays,p.data['validation']['bounds_tolerance_m'])['status']=='PASS'
    assert embedded_bytes(p.path('output/viewer.html').read_text())==p.glb.read_bytes()
    qa=read_json(p.path('validation/viewer_qa.json'))
    assert qa['status']=='PASS' and qa['mobile']['initial']['errors']==[]
    assert verify_manifest(p)
