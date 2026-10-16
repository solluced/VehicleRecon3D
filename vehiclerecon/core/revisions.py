"""Deterministic canonical authoring identity; no mtime-based concurrency."""
import json
import re
from pathlib import Path
from .manifest import digest_data
from .errors import SchemaError

AUTHORED = {'calibration', 'cage', 'surface_graph', 'details', 'silhouette_traces'}
DECISIONS = ('validation/source_review.json', 'validation/cage_review.json', 'validation/review.json')

def candidate_path(path):
    return bool(re.fullmatch(r'validation/rectification_candidates/[A-Za-z_][A-Za-z0-9_.-]{0,159}\.json',path))


def safe_path(root, relative):
    from .project import Project
    p = object.__new__(Project)
    p.root = Path(root).resolve()
    return p.path(relative)


def canonical_paths(data):
    return {'project.json', *[p for kind, p in data.get('generated', {}).items() if kind in AUTHORED],
            *data.get('references', {}).values(), *DECISIONS}


def snapshot(root):
    root = Path(root).resolve()
    path = root/'project.json'
    raw = path.read_bytes() if path.is_file() else None
    data = json.loads(raw.decode('utf-8-sig')) if raw else {}
    result = {}
    for relative in sorted(canonical_paths(data)):
        target = safe_path(root, relative)
        result[relative] = target.read_bytes() if target.is_file() else None
    directory = safe_path(root, 'validation/rectification_candidates')
    if directory.is_dir():
        paths = list(directory.glob('*.json'))
        if len(paths)>1000:raise SchemaError('Too many rectification candidates')
        for path in paths:
            relative = path.relative_to(root).as_posix()
            if candidate_path(relative):result[relative] = safe_path(root,relative).read_bytes()
    return result


def revision(root):
    import hashlib
    return digest_data({p: hashlib.sha256(raw).hexdigest() if raw is not None else None
                        for p, raw in snapshot(root).items()})
