"""Deterministic identities; timestamps are deliberately excluded."""
import hashlib
import json
from pathlib import Path
from .errors import SchemaError


def digest_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (ValueError, TypeError) as exc:
        raise SchemaError(str(exc)) from exc


def digest_data(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def manifest(root, paths):
    root = Path(root).resolve()
    result = []
    for path in sorted({Path(p).resolve() for p in paths}):
        if not path.is_relative_to(root) or not path.is_file():
            raise SchemaError(f"Manifest path outside project or missing: {path}")
        result.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size,
                       "sha256": digest_file(path)})
    return result
