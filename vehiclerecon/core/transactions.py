"""Journalled multi-file commits and hash-checked recovery under ProjectLock."""
import base64
import hashlib
import json
import os
import uuid
import re
from .errors import ConflictError, SchemaError
from .locking import ProjectLock
from .revisions import safe_path, revision, canonical_paths, DECISIONS, AUTHORED, candidate_path

PENDING = '.cache/authoring/pending.json'


def encoded(value):
    return base64.b64encode(value).decode('ascii') if value is not None else None


def decoded(value):
    return base64.b64decode(value, validate=True) if value is not None else None


def digest(value):
    return hashlib.sha256(value).hexdigest() if value is not None else None


def atomic_write(root, relative, raw):
    path = safe_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path = safe_path(root, relative)
    temporary = safe_path(root, relative+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        if safe_path(root, relative) != path:
            raise ConflictError('Transaction destination changed')
        os.replace(temporary, path)
        if os.name != 'nt':
            descriptor = os.open(path.parent, os.O_RDONLY)
            try:os.fsync(descriptor)
            finally:os.close(descriptor)
    finally:
        if temporary.is_file():temporary.unlink()


def _json(root, relative, data):
    atomic_write(root, relative, (json.dumps(data, indent=2, allow_nan=False)+'\n').encode('utf-8'))


def _allowed(projects):
    result = {'project.json', *DECISIONS}
    for data in projects:
        result.update(path for kind, path in data.get('generated', {}).items() if kind in AUTHORED)
    return result


def recover(root, *, prefer='new', locked=False):
    if not locked:
        with ProjectLock(root, 'transaction-recovery'):
            return recover(root, prefer=prefer, locked=True)
    pending = safe_path(root, PENDING)
    if not pending.is_file():return None
    marker = json.loads(pending.read_text(encoding='utf-8'))
    journal_path = marker['journal']
    if not re.fullmatch(r'\.cache/authoring/transactions/[0-9a-f]{32}\.json', journal_path):
        raise ConflictError('Invalid recovery journal identity')
    journal = json.loads(safe_path(root, journal_path).read_text(encoding='utf-8'))
    project_entries = [e for e in journal['entries'] if e['path'] == 'project.json']
    projects = []
    for entry in project_entries:
        for key in ('old', 'new'):
            raw = decoded(entry[key])
            if raw is not None:projects.append(json.loads(raw.decode('utf-8-sig')))
    if not projects:
        projects = [json.loads(safe_path(root, 'project.json').read_text(encoding='utf-8-sig'))]
    allowed = _allowed(projects)
    protected = {path for data in projects for path in data.get('references', {}).values()}
    for entry in journal['entries']:
        if any(digest(decoded(entry[key])) != entry[key+'_sha256'] for key in ('old','new')):
            raise ConflictError('Recovery journal content hash mismatch')
        if (entry['path'] not in allowed and not candidate_path(entry['path'])) or entry['path'] in protected:
            raise ConflictError('Journal targets a noncanonical or protected source file')
        path = safe_path(root, entry['path'])
        actual = path.read_bytes() if path.is_file() else None
        if actual not in (decoded(entry['old']), decoded(entry['new'])):
            raise ConflictError('External edit prevents transaction recovery: '+entry['path'])
    for entry in journal['entries']:
        raw = decoded(entry[prefer]);path = safe_path(root, entry['path'])
        actual = path.read_bytes() if path.is_file() else None
        if actual not in (decoded(entry['old']), decoded(entry['new'])):
            raise ConflictError('External edit during transaction recovery: '+entry['path'])
        if raw is None:
            if path.is_file():path.unlink()
        else:atomic_write(root, entry['path'], raw)
    journal['state'] = 'COMMITTED' if prefer == 'new' else 'ROLLED_BACK'
    _json(root, journal_path, journal)
    pending.unlink()
    return {'transaction_id': journal['id'], 'state': journal['state'], 'revision': revision(root)}


def commit(root, changes, *, expected_revision, validator, operation='authoring', fault=None):
    """Lower-level canonical storage primitive; callers expose typed commands."""
    with ProjectLock(root, operation, expected_revision):
        recover(root, locked=True)
        if revision(root) != expected_revision:
            raise ConflictError('CONFLICT: canonical inputs changed externally')
        original = safe_path(root, 'project.json').read_bytes()
        old_project = json.loads(original.decode('utf-8-sig'))
        new_project = json.loads(changes.get('project.json', original).decode('utf-8-sig'))
        allowed = _allowed([old_project, new_project])
        sources = {p for d in (old_project, new_project) for p in d.get('references', {}).values()}
        if any(p not in allowed and not candidate_path(p) for p in changes) or set(changes) & sources:
            raise SchemaError('Transaction may edit only canonical JSON and acceptance records')
        files = {}
        from .revisions import snapshot
        files.update({p:raw for p,raw in snapshot(root).items() if candidate_path(p) and raw is not None})
        for path in allowed:
            target = safe_path(root, path)
            if target.is_file():files[path] = target.read_bytes()
        for path, raw in changes.items():
            if raw is None:files.pop(path, None)
            else:files[path] = raw
        validator(files)
        if revision(root) != expected_revision:
            raise ConflictError('CONFLICT: inputs changed during validation')
        entries = []
        resolved = set()
        for relative, new in sorted(changes.items()):
            target = safe_path(root, relative)
            if target in resolved:raise SchemaError('Aliased transaction targets')
            resolved.add(target)
            old = target.read_bytes() if target.is_file() else None
            if old != new:
                entries.append({'path': relative, 'old': encoded(old), 'new': encoded(new),
                                'old_sha256': digest(old), 'new_sha256': digest(new)})
        if not entries:
            return {'revision': expected_revision, 'changed_files': [], 'transaction_id': None}
        identity = uuid.uuid4().hex
        journal_path = '.cache/authoring/transactions/'+identity+'.json'
        journal = {'id': identity, 'state': 'PREPARED', 'base_revision': expected_revision, 'entries': entries}
        _json(root, journal_path, journal)
        _json(root, PENDING, {'journal': journal_path})
        try:
            if fault:fault('prepared')
            for entry in entries:
                target = safe_path(root, entry['path'])
                actual = target.read_bytes() if target.is_file() else None
                if actual != decoded(entry['old']):
                    raise ConflictError('External edit during transaction')
                raw = decoded(entry['new'])
                if raw is None:
                    if target.is_file():target.unlink()
                else:atomic_write(root, entry['path'], raw)
                if fault:fault('replaced:'+entry['path'])
            for entry in entries:
                target = safe_path(root, entry['path'])
                if (target.read_bytes() if target.is_file() else None) != decoded(entry['new']):
                    raise ConflictError('External edit before commit')
            journal['state'] = 'COMMITTED';_json(root, journal_path, journal)
            safe_path(root, PENDING).unlink()
        except Exception:
            recover(root, prefer='old', locked=True)
            raise
        return {'revision': revision(root), 'transaction_id': identity,
                'changed_files': [{k: e[k] for k in ('path', 'old_sha256', 'new_sha256')} for e in entries]}
