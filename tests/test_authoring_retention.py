import shutil
from pathlib import Path
from vehiclerecon.authoring.service import AuthoringSession


def test_delta_history_is_reversible_and_count_retention_is_explicit(tmp_path):
    shutil.copytree(Path(__file__).parent/'fixtures/authoring_v2',tmp_path,dirs_exist_ok=True)
    s=AuthoringSession(tmp_path,history_limit=2)
    revisions=[]
    for name in ('one','two','three'):
        revisions.append(s.apply([{'type':'SetProjectMetadata','values':{'asset_name':name}}],expected_revision=s.revision)['revision'])
    assert len(s.undo_stack)==2
    assert set(s.undo_stack[-1]['before'])=={'project.json'}
    assert s.undo_stack[-1]['before']['project.json'] is s.undo_stack[-2]['after']['project.json']
    s.undo(expected_revision=s.revision);assert s.revision==revisions[1]
    s.undo(expected_revision=s.revision);assert s.revision==revisions[0]
    s.redo(expected_revision=s.revision);assert s.revision==revisions[1]


def test_byte_retention_drops_oldest_edge_without_corrupting_current_state(tmp_path):
    shutil.copytree(Path(__file__).parent/'fixtures/authoring_v2',tmp_path,dirs_exist_ok=True)
    s=AuthoringSession(tmp_path,history_byte_limit=20000)
    for i in range(8):s.apply([{'type':'MoveObservation','observation_id':'obs_roof_side','pixel':[128+i,78]}],expected_revision=s.revision)
    assert s.history_retained_bytes<=20000
    assert s.undo_stack
    before=s.undo_stack[-1]['before_revision'];s.undo(expected_revision=s.revision)
    assert s.revision==before
