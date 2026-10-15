import copy
import json
import shutil
from pathlib import Path
import pytest
from vehiclerecon.core.project import Project, validate, read_json
from vehiclerecon.core.errors import SchemaError, ReferenceError
from vehiclerecon.core.manifest import canonical, manifest
from vehiclerecon.blender.runner import discover, run

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def project(tmp_path):
    source = ROOT / 'projects/tesla'
    shutil.copytree(source/'input', tmp_path/'input')
    shutil.copyfile(source/'project.json', tmp_path/'project.json')
    shutil.copytree(source/'generated', tmp_path/'generated')
    return Project(tmp_path)

def test_project(project):
    assert project.data['category'] == 'automobile'
    assert project.profile['id'] == project.data['vehicle_profile']

@pytest.mark.parametrize('value', [0, -1, float('nan'), float('inf'), True])
def test_bad_dimensions(project, value):
    data = copy.deepcopy(project.data)
    data['dimensions']['length_m'] = value
    with pytest.raises(SchemaError):
        validate(data, 'project')

@pytest.mark.parametrize('path', ['../secret', '/etc/secret', 'C:/secret', 'a/../../secret', 'C:secret', r'a\..\secret', '//host/share/file'])
def test_unsafe_paths(project, path):
    with pytest.raises(ReferenceError):
        project.path(path)

def test_missing_file(project):
    with pytest.raises(ReferenceError):
        project.path('input/missing.png', exists=True)

def test_schema_version(project):
    bad = copy.deepcopy(project.data)
    bad['schema_version'] = 2
    with pytest.raises(SchemaError):
        validate(bad, 'project')

def test_additional_properties(project):
    bad = copy.deepcopy(project.data)
    bad['execute'] = 'some_python()'
    with pytest.raises(SchemaError):
        validate(bad, 'project')

def test_profile_floor_cannot_be_weakened(project):
    data=copy.deepcopy(project.data);data['validation']['thresholds']['side']=.1
    (project.root/'project.json').write_text(json.dumps(data))
    with pytest.raises(SchemaError):Project(project.root)

def test_profile_path_rejected_even_in_worker(project):
    data=copy.deepcopy(project.data);data['vehicle_profile']='../outside'
    (project.root/'project.json').write_text(json.dumps(data))
    with pytest.raises(SchemaError):Project(project.root,check=False)

def test_nonfinite_json(tmp_path):
    p = tmp_path/'bad.json'
    p.write_text('{"value":NaN}')
    with pytest.raises(SchemaError):
        read_json(p)

def test_manifest(project):
    first = manifest(project.root, [project.root/'project.json'])
    assert first == manifest(project.root, [project.root/'project.json'])
    assert first[0]['sha256']
    assert canonical({'b':1,'a':2}) == canonical({'a':2,'b':1})

def test_schemas_well_formed():
    from jsonschema import Draft202012Validator
    for p in (ROOT/'schemas').glob('*.json'):
        Draft202012Validator.check_schema(read_json(p))

@pytest.mark.blender
def test_fresh_blender_scene(project):
    evidence = run(project, 'initialize')
    assert '--python-exit-code' in evidence['command']
    assert evidence['returncode'] == 0
    assert project.path('.cache/initialize.blend').is_file()
