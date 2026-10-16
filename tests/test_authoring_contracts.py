import copy
import shutil
import pytest
from vehiclerecon.core.project import Project, REPOSITORY, validate
from vehiclerecon.core.errors import SchemaError, ReferenceError
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.authoring.contracts import semantic_check

FIXTURE = REPOSITORY/'tests/fixtures/authoring_v2'


@pytest.fixture
def authoring_root(tmp_path):
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    return tmp_path


def test_v1_and_v2_load_without_automatic_migration(authoring_root):
    assert Project(REPOSITORY/'projects/tesla').data['schema_version'] == 1
    workspace = Workspace(authoring_root)
    assert workspace.project.data['schema_version'] == 2
    assert len(workspace.documents['calibration']['correspondences']) == 4
    raw = workspace.documents['cage']['curves'][0]['points'][1]
    assert isinstance(raw, dict)
    assert workspace.project.generated('cage')['curves'][0]['points'][1] == (0, .5, 1)


@pytest.mark.parametrize('kind', ['point','polyline','spline','circle','measurement','axis'])
def test_typed_observation_kinds(authoring_root, kind):
    document = copy.deepcopy(Workspace(authoring_root).documents['calibration'])
    observation = document['views']['side']['landmarks']['observations'][0]
    observation.pop('pixel');observation['kind'] = kind
    if kind == 'point':observation['pixel'] = [100,100]
    if kind in ('polyline','spline','axis'):
        observation['points'] = [{'id':'knot_one','pixel':[0,0]}, {'id':'knot_two','pixel':[1,1]}]
    if kind == 'circle':observation.update(center=[100,100],radius_px=20)
    if kind == 'measurement':observation['measurement_id'] = 'wheelbase'
    validate(document, 'calibration')
    observation['renderer_json'] = {}
    with pytest.raises(SchemaError):validate(document, 'calibration')


@pytest.mark.parametrize('mutation', ['missing','duplicate','stale','world','point','crop','view'])
def test_broken_bindings_fail_explicitly(authoring_root, mutation):
    w = Workspace(authoring_root);c = copy.deepcopy(w.documents['calibration']);g = copy.deepcopy(w.documents['cage'])
    link = c['correspondences'][0]
    if mutation == 'missing':link['observation_id'] = 'absent'
    if mutation == 'duplicate':c['correspondences'].append(dict(link,id='other_link'))
    if mutation == 'stale':link['observation_revision'] = 42
    if mutation == 'world':link['world_entity_id'] = 'absent'
    if mutation == 'point':link.update(binding_type='curve_point',world_entity_id='roof_edge',point_id='absent')
    if mutation == 'crop':c['views']['side']['landmarks']['observations'][0]['crop_id'] = '0'*64
    if mutation == 'view':c['views']['side']['landmarks']['observations'][0]['view'] = 'top'
    with pytest.raises((SchemaError,ReferenceError)):
        semantic_check(w.project,c,g)


def test_unsupported_future_version(authoring_root):
    from vehiclerecon.core.manifest import write_json
    w = Workspace(authoring_root);data = copy.deepcopy(w.project.data);data['schema_version'] = 99
    write_json(authoring_root/'project.json',data)
    with pytest.raises(SchemaError):Project(authoring_root)
