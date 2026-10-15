from pathlib import Path
from types import SimpleNamespace
import pytest
from vehiclerecon.core.pipeline import Pipeline,Stage,StageResult,Status,STAGES,dependency_order
from vehiclerecon.core.errors import SchemaError,GateError,BlockedError
from vehiclerecon.cli import main

def project(tmp_path):
    return SimpleNamespace(path=lambda relative:tmp_path/relative)

def test_order():
    actual=dependency_order(list(reversed(STAGES)))
    positions={s.id:i for i,s in enumerate(actual)}
    for s in actual:
        assert all(positions[d]<positions[s.id] for d in s.dependencies)

def test_order_errors():
    with pytest.raises(SchemaError):dependency_order([Stage('a','a',('missing',))])
    with pytest.raises(SchemaError):dependency_order([Stage('a','a',('b',)),Stage('b','b',('a',))])

@pytest.mark.parametrize('failure',[GateError('failed'),BlockedError('review missing')])
def test_fail_and_blocked_exit(tmp_path,failure):
    p=Pipeline(project(tmp_path));actions={s.id:lambda:[] for s in STAGES}
    def fail():raise failure
    actions['silhouette']=fail
    assert p.run(actions=actions)==1
    assert p.results[7].status==Status.BLOCKED
    assert p.results[6].status==(Status.BLOCKED if isinstance(failure,BlockedError) else Status.FAIL)

def test_success(tmp_path):
    p=Pipeline(project(tmp_path));assert p.run(actions={s.id:lambda:[] for s in STAGES})==0
    assert len(p.results)==14
    assert all(r.status==Status.PASS for r in p.results)

def test_result_exit_codes():
    for status in Status:assert StageResult('x',status).exit_code==(0 if status in [Status.PASS,Status.SKIP] else 1)

def test_init_does_not_invent_geometry(tmp_path):
    from vehiclerecon.core.project import read_json
    assert main(['init',str(tmp_path/'example')])==0
    data=read_json(tmp_path/'example/project.json')
    assert data['dimensions']['length_m'] is None
    assert not list((tmp_path/'example').rglob('*.py'))
    assert main(['inspect',str(tmp_path/'example')])==1
    assert main(['init',str(tmp_path/'example')])==1

def test_inspect_cli():
    from vehiclerecon.core.project import REPOSITORY
    assert main(['inspect',str(REPOSITORY/'projects/tesla')])==0
