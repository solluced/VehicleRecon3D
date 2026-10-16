import copy
import json
import shutil
import subprocess
import sys
import threading
import pytest
from vehiclerecon.core.project import Project, REPOSITORY
from vehiclerecon.core.errors import ConflictError, LockError, SchemaError
from vehiclerecon.core.locking import ProjectLock
from vehiclerecon.core.revisions import revision
from vehiclerecon.core.transactions import commit, recover, PENDING
from vehiclerecon.authoring.workspace import Workspace


@pytest.fixture
def root(tmp_path):
    shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2', tmp_path, dirs_exist_ok=True)
    return tmp_path


def changes(w):
    project = copy.deepcopy(w.documents['project']);project['asset_name'] = 'renamed_fixture'
    cage = copy.deepcopy(w.documents['cage']);cage['landmarks']['roof_corner'][0] = .02
    return {'project.json':(json.dumps(project,indent=2)+'\n').encode(),
            'generated/cage.json':(json.dumps(cage,indent=2)+'\n').encode()}


def test_multi_file_commit_and_revision(root):
    w = Workspace(root);before = w.revision
    result = commit(root,changes(w),expected_revision=before,validator=w.validate)
    assert len(result['changed_files']) == 2
    assert revision(root) == result['revision'] != before
    assert Workspace(root).documents['cage']['landmarks']['roof_corner'][0] == .02
    assert not (root/PENDING).exists()


def test_reject_stale_and_external_edit_without_partial_write(root):
    w = Workspace(root);original = (root/'generated/cage.json').read_bytes()
    (root/'project.json').write_bytes((root/'project.json').read_bytes()+b'\n')
    with pytest.raises(ConflictError):commit(root,changes(w),expected_revision=w.revision,validator=w.validate)
    assert (root/'generated/cage.json').read_bytes() == original


@pytest.mark.parametrize('fault_at', ['prepared','replaced:generated/cage.json','replaced:project.json'])
def test_crash_recovery_and_loader_cooperation(root, fault_at):
    class Crash(BaseException):pass
    w = Workspace(root);after = changes(w)
    def crash(point):
        if point == fault_at:raise Crash()
    with pytest.raises(Crash):commit(root,after,expected_revision=w.revision,validator=w.validate,fault=crash)
    assert (root/PENDING).exists()
    Project(root)  # Acquires shared lock and recovers before loading either document.
    for path, raw in after.items():assert (root/path).read_bytes() == raw
    assert not (root/PENDING).exists()


def test_ordinary_failure_rolls_back(root):
    w = Workspace(root);before = revision(root)
    def fail(point):
        if point.startswith('replaced:'):raise OSError('injected write failure')
    with pytest.raises(OSError):commit(root,changes(w),expected_revision=before,validator=w.validate,fault=fail)
    assert revision(root) == before and not (root/PENDING).exists()


def test_recovery_never_overwrites_unexpected_third_party_edit(root):
    class Crash(BaseException):pass
    w = Workspace(root)
    def crash(point):
        if point.startswith('replaced:'):raise Crash()
    with pytest.raises(Crash):commit(root,changes(w),expected_revision=w.revision,validator=w.validate,fault=crash)
    target = root/'generated/cage.json';external = target.read_bytes()+b'\n\n';target.write_bytes(external)
    with pytest.raises(ConflictError):recover(root)
    assert target.read_bytes() == external and (root/PENDING).exists()


def test_invalid_transaction_and_source_changes_rejected(root):
    w = Workspace(root);before = revision(root)
    for change in ({'input/reference.png':b'not an image'}, {'../escape.json':b'{}'},
                   {'project.json':b'{}'}):
        with pytest.raises(SchemaError):commit(root,change,expected_revision=before,validator=w.validate)
        assert revision(root) == before


def test_reentrant_lock_and_thread_conflict(root):
    result = []
    def other():
        try:
            with ProjectLock(root):result.append('incorrectly acquired')
        except LockError:result.append('conflict')
    with ProjectLock(root,'outer'):
        with ProjectLock(root,'nested'):
            thread = threading.Thread(target=other);thread.start();thread.join(timeout=10)
            assert not thread.is_alive() and result == ['conflict']
    with ProjectLock(root):pass


def test_real_cross_process_lock_conflict(root):
    code = "from vehiclerecon.core.locking import ProjectLock; import sys; lock=ProjectLock(sys.argv[1],'child'); lock.__enter__(); print('LOCKED',flush=True); sys.stdin.readline(); lock.__exit__()"
    process = subprocess.Popen([sys.executable,'-c',code,str(root)],stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=REPOSITORY)
    try:
        assert process.stdout.readline().strip() == 'LOCKED'
        with pytest.raises(LockError):
            with ProjectLock(root):pass
    finally:
        process.communicate('\n',timeout=10)
    assert process.returncode == 0
    with ProjectLock(root):pass
