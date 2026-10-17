import copy
import shutil
import pytest
from vehiclerecon.core.project import REPOSITORY, Project
from vehiclerecon.core.errors import ConflictError, SchemaError
from vehiclerecon.authoring.service import AuthoringSession
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.authoring.versions import create_draft
from vehiclerecon.authoring.imports import import_reference


def test_import_unknown_scale_draft_exact_bytes_and_undo(tmp_path):
    create_draft(tmp_path);session=AuthoringSession(tmp_path);before=session.revision
    raw=(REPOSITORY/'tests/fixtures/authoring_v2/input/reference.png').read_bytes()
    result=import_reference(session,raw,expected_revision=before)
    w=Workspace(tmp_path)
    assert w.documents['project']['dimensions']['length_m'] is None
    assert (tmp_path/w.documents['project']['references']['multiview']).read_bytes()==raw
    assert 'origin' not in w.documents['calibration']['views']['side']
    session.undo(expected_revision=result['revision']);assert session.revision==before
    session.redo(expected_revision=session.revision);assert session.revision==result['revision']


def test_metadata_and_source_properties_typed_reversible(tmp_path):
    shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',tmp_path,dirs_exist_ok=True)
    s=AuthoringSession(tmp_path);before=s.revision
    s.apply([{'type':'SetProjectMetadata','values':{'asset_name':'Manual_Study'}},
             {'type':'SetObservationProperties','observation_id':'obs_roof_side','values':{'uncertainty_px':3,'provenance':{'type':'inferred','method':'Human hypothesis'},'visibility':'inferred','measured':False}}],expected_revision=before)
    w=Workspace(tmp_path)
    assert w.documents['project']['asset_name']=='Manual_Study'
    assert w.documents['calibration']['views']['side']['landmarks']['observations'][0]['uncertainty_px']==3
    s.undo(expected_revision=s.revision);assert s.revision==before
    for values in ({'source_sha256':'0'*64},{'id':'rebind'},{'semantic_role':'invented_ontology'}):
        with pytest.raises(SchemaError):s.apply([{'type':'SetObservationProperties','observation_id':'obs_roof_side','values':values}],expected_revision=s.revision)


def test_changed_profile_validates_against_actual_profile(tmp_path):
    create_draft(tmp_path);s=AuthoringSession(tmp_path);before=s.revision
    with pytest.raises(SchemaError):s.apply([{'type':'SetProjectMetadata','values':{'vehicle_profile':'not_available'}}],expected_revision=before)
    assert s.revision==before


def test_reused_readiness_matches_fresh_and_rejects_stale_workspace(tmp_path):
    from vehiclerecon.authoring.readiness import readiness
    shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',tmp_path,dirs_exist_ok=True)
    w=Workspace(tmp_path)
    assert readiness(tmp_path,workspace=w)==readiness(tmp_path)
    path=tmp_path/'project.json';path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ConflictError):readiness(tmp_path,workspace=w)
