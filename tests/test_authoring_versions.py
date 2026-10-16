import copy
import json
import shutil
import pytest
from vehiclerecon.core.project import Project, REPOSITORY
from vehiclerecon.core.revisions import revision
from vehiclerecon.core.errors import SchemaError, ConflictError
from vehiclerecon.authoring.versions import inspect_version, preview_migration, execute_migration, create_draft
from vehiclerecon.authoring.workspace import Workspace


@pytest.fixture
def legacy(tmp_path):
    base = REPOSITORY/'projects/tesla'
    shutil.copyfile(base/'project.json',tmp_path/'project.json')
    for folder in ('input','generated'):shutil.copytree(base/folder,tmp_path/folder)
    return tmp_path


def test_preview_is_explicit_and_preserves_geometry(legacy):
    before = revision(legacy);project = Project(legacy);old = project.generated('cage')
    plan = preview_migration(legacy)
    assert revision(legacy) == before and inspect_version(legacy)['version'] == 1
    assert plan['manual_authoring_required'] and plan['source_version'] == 1
    new = plan['documents'][project.data['generated']['cage']]
    assert [c['points'] for c in new['curves']] == [c['points'] for c in old['curves']]
    assert plan['documents'][project.data['generated']['calibration']]['correspondences'] == []
    assert not (legacy/'validation/source_review.json').exists()


def test_backup_precedes_mutation_and_migration_never_accepts(legacy):
    before = revision(legacy)
    def check(point):
        assert list((legacy/'.cache/authoring/checkpoints').glob('*.json'))
    result = execute_migration(legacy,expected_revision=before,fault=check)
    backup = json.loads((legacy/result['backup']).read_text())
    assert backup['source_revision'] == before and backup['files']['project.json']
    w = Workspace(legacy)
    assert w.project.data['authoring_state'] == 'DRAFT'
    assert w.documents['calibration']['authoring_policy']['coverage_confirmed'] is False
    assert w.documents['calibration']['correspondences'] == []
    assert not (legacy/'validation/source_review.json').exists()
    assert result['changed_files'] and result['source_hashes'] and result['warnings']
    with pytest.raises(SchemaError):preview_migration(legacy)


def test_migration_conflict_has_no_backup_or_changes(legacy):
    before = revision(legacy);path = legacy/'project.json';path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ConflictError):execute_migration(legacy,expected_revision=before)
    assert inspect_version(legacy)['version'] == 1
    assert not (legacy/'.cache/authoring/checkpoints').exists()


def test_future_readonly_and_unknown_draft_values(tmp_path):
    create_draft(tmp_path)
    w = Workspace(tmp_path)
    assert w.project.data['dimensions']['wheelbase_m'] is None
    assert inspect_version(tmp_path)['valid']
    path = tmp_path/'project.json';data = json.loads(path.read_text());data['schema_version'] = 55
    path.write_text(json.dumps(data))
    info = inspect_version(tmp_path)
    assert info['read_only'] and not info['supported'] and not info['valid']
    with pytest.raises(SchemaError):Project(tmp_path)
