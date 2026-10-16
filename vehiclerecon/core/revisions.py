"""Deterministic canonical authoring identity; no mtime-based concurrency."""
import json
from pathlib import Path
from .manifest import digest_data
from .errors import SchemaError

AUTHORED = {'calibration', 'cage', 'surface_graph', 'details', 'silhouette_traces'}
DECISIONS = ('validation/source_review.json', 'validation/cage_review.json', 'validation/review.json')


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
    return result


def revision(root):
    import hashlib
    return digest_data({p: hashlib.sha256(raw).hexdigest() if raw is not None else None
                        for p, raw in snapshot(root).items()})
