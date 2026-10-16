"""Reentrant per-thread, nonblocking cross-process mutation lock."""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from .errors import LockError, ReferenceError

_guard = threading.Lock()
_owners = {}


class ProjectLock:
    def __init__(self, root, operation='authoring', acquired_revision=None):
        self.root = Path(root).resolve()
        self.key = str(self.root).casefold() if os.name == 'nt' else str(self.root)
        self.operation = operation
        self.revision = acquired_revision
        self.entered = False

    def __enter__(self):
        if not self.root.is_dir():
            raise ReferenceError('Project root must exist before locking')
        thread = threading.get_ident()
        with _guard:
            owner = _owners.get(self.key)
            if owner:
                if owner['thread'] != thread:
                    raise LockError('Project locked by another thread: '+owner['operation'])
                owner['depth'] += 1
                self.entered = True
                return self
            from .revisions import safe_path, revision
            path = safe_path(self.root, '.cache/project.lock')
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                handle = path.open('x+b')
            except FileExistsError:
                handle = path.open('r+b')
            try:
                handle.seek(0, 2)
                if handle.tell() == 0:
                    handle.write(b' ');handle.flush()
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                handle.close()
                raise LockError('Project locked by another process') from exc
            try:
                metadata = {'pid': os.getpid(), 'thread': thread, 'operation': self.operation,
                            'acquired_revision': self.revision or revision(self.root),
                            'acquired_at': datetime.now(timezone.utc).isoformat()}
                handle.seek(1);handle.truncate();handle.write(json.dumps(metadata).encode('utf-8'));handle.flush()
                _owners[self.key] = {'thread': thread, 'depth': 1, 'handle': handle, 'operation': self.operation}
                self.entered = True
            except BaseException:
                handle.close()
                raise
        return self

    def __exit__(self, *args):
        if not self.entered:
            return
        with _guard:
            owner = _owners[self.key]
            owner['depth'] -= 1
            if owner['depth'] == 0:
                handle = owner['handle'];handle.seek(0)
                try:
                    if os.name == 'nt':
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                finally:
                    handle.close();del _owners[self.key]
            self.entered = False
