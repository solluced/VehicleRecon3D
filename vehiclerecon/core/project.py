"""Validated project loading without Blender imports or vehicle constants."""
import json
import math
import re
import sys
from functools import lru_cache
from collections import OrderedDict
from contextvars import ContextVar
from contextlib import contextmanager
import threading
from pathlib import Path, PureWindowsPath
from .errors import SchemaError, ReferenceError

REPOSITORY = Path(__file__).resolve().parents[2]
RESOURCE_ROOT = next((root for root in [REPOSITORY,REPOSITORY/'share/vehiclerecon',
    *[p/'share/vehiclerecon' for p in list(REPOSITORY.parents)[:3]],Path(sys.prefix)/'share/vehiclerecon']
    if (root/'schemas/project.schema.json').is_file()),REPOSITORY)

_structural_cache=OrderedDict();_structural_bytes=0
_structural_lock=threading.RLock();_audit_validation=ContextVar('full_schema_audit',default=False)

@contextmanager
def full_validation():
    """Bypass positive structural memoization; semantic validation always runs."""
    token=_audit_validation.set(True)
    try:yield
    finally:_audit_validation.reset(token)

def structural_cache_metrics():
    with _structural_lock:return {'entries':len(_structural_cache),'bytes':_structural_bytes,'limit_bytes':16*1024*1024}

def _json_types(value):
    if type(value) is dict:return all(type(k) is str and _json_types(v) for k,v in value.items())
    if type(value) is list:return all(_json_types(v) for v in value)
    return type(value) in (str,int,float,bool,type(None))


def finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise SchemaError("NaN and Infinity are forbidden")
    if isinstance(value, dict):
        for child in value.values():
            finite(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            finite(child)


def read_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8-sig"),
                           parse_constant=lambda s: (_ for _ in ()).throw(SchemaError(f"Nonfinite: {s}")))
        finite(value)
        return value
    except (OSError, ValueError) as exc:
        raise SchemaError(f"{path}: {exc}") from exc


@lru_cache(maxsize=4)
def _schema_bundle(entries):
    """Reuse parsed schemas and immutable registries, keyed to exact disk bytes.

    The filesystem is still read on every validation; neither mtime nor a previous
    semantic result establishes current validity. Each call gets its own validator.
    """
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    import hashlib
    schemas={}
    for name,raw in entries:
        value=json.loads(raw.decode('utf-8-sig'));finite(value);schemas[name]=value
    registry=Registry().with_resources((s['$id'],Resource.from_contents(s)) for s in schemas.values())
    identity=hashlib.sha256(b'\0'.join(name.encode()+b'\0'+raw for name,raw in entries)).hexdigest()
    return schemas,registry,identity


def validate(value, schema_name, *, full=False):
    global _structural_bytes
    from jsonschema import Draft202012Validator
    schema_root = RESOURCE_ROOT / "schemas"
    if schema_name in ('project','calibration','cage') and value.get('schema_version') == 2:
        schema_name += '_v2'
    try:schemas,registry,identity=_schema_bundle(tuple((p.name,p.read_bytes()) for p in sorted(schema_root.glob('*.schema.json'))))
    except (OSError,ValueError) as exc:raise SchemaError('Invalid local schema bundle') from exc
    schema = schemas[f'{schema_name}.schema.json']
    finite(value)
    key=None
    if not full and not _audit_validation.get() and _json_types(value):
        raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        if len(raw)<=8*1024*1024:
            key=(identity,schema_name,raw)
            with _structural_lock:
                if key in _structural_cache:
                    _structural_cache.move_to_end(key);return
    validator = Draft202012Validator
    if schema_name in ('calibration_v2','authoring_command','authoring') and not (full or _audit_validation.get()):
        from .schema_dispatch import authoring_validator, validation_namespace
        validator = authoring_validator()
        context=validation_namespace(None,identity=identity)
    else:
        from contextlib import nullcontext
        context=nullcontext()
    with context:
        errors = sorted(validator(schema, registry=registry).iter_errors(value),
                    key=lambda e: str(list(e.path)))
    if errors:
        raise SchemaError("; ".join(f"{'/'.join(map(str,e.path))}: {e.message}" for e in errors))
    if key is not None:
        with _structural_lock:
            if key not in _structural_cache:_structural_cache[key]=True;_structural_bytes+=len(key[2])
            while len(_structural_cache)>128 or _structural_bytes>16*1024*1024:
                old,_=_structural_cache.popitem(last=False);_structural_bytes-=len(old[2])


class Project:
    def __init__(self, root, *, check=True):
        self.root = Path(root).resolve()
        from .locking import ProjectLock
        from .transactions import recover
        with ProjectLock(self.root, 'project-read'):
            recover(self.root, locked=True)
            self._load(check=check)

    def _load(self, *, check):
        self.data = read_json(self.root / "project.json")
        version = self.data.get("schema_version")
        if version not in (1,2):
            raise SchemaError("Unsupported project schema_version")
        if check:
            validate(self.data, "project")
        for name, value in self.data.get("dimensions", {}).items():
            if version == 2 and self.data.get('authoring_state') == 'DRAFT' and value is None:
                continue
            if name.endswith("_m") and (not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0):
                raise SchemaError(f"Dimension must be positive: {name}")
        if not re.fullmatch('[a-z_]+',self.data['vehicle_profile']):
            raise SchemaError('Unsafe vehicle profile identifier')
        self.profile = read_json(RESOURCE_ROOT / "profiles" / f"{self.data['vehicle_profile']}.json")
        if check:
            validate(self.profile, "vehicle_profile")
        for view,minimum in self.profile.get('minimum_iou',{}).items():
            if version == 2 and self.data.get('authoring_state') == 'DRAFT' and not self.data.get('validation'):
                break
            if self.data['validation']['thresholds'][view]<minimum:
                raise SchemaError(f'{view}: project threshold cannot weaken profile floor {minimum}')
        allowed_roles=set(self.profile['roles'])|set(self.profile['optional_roles'])
        if set(self.data.get('roles',{}))-allowed_roles:
            raise SchemaError('Project has semantic roles outside its vehicle profile')
        if (version == 1 or self.data.get('authoring_state') == 'READY') and set(self.profile['roles'])-set(self.data.get('roles',{})):
            raise SchemaError('Required semantic role bindings are missing')
        if self.data.get('export') and set(self.data['export']['collections'])&set(self.data['export']['excluded_collections']):
            raise SchemaError('Export model collections cannot be excluded from silhouette validation')
        for path in self.data["references"].values():
            self.path(path, exists=True)
        for path in self.data.get("generated", {}).values():
            self.path(path, exists=True)
        for folder in ("input", "generated", "validation", "output", ".cache"):
            self.path(folder).mkdir(exist_ok=True)

    @classmethod
    def worker_snapshot(cls, root):
        """Trusted worker read under the parent runner's held project lock.

        The worker must not acquire its parent's exclusive OS lock. This is an
        internal read-only construction path, never an authoring write API.
        """
        project = object.__new__(cls)
        project.root = Path(root).resolve()
        project._load(check=False)
        return project

    def path(self, relative, *, exists=False):
        if not isinstance(relative, str) or not relative or "\\" in relative:
            raise ReferenceError(f"Use nonempty project-relative POSIX paths: {relative!r}")
        win = PureWindowsPath(relative)
        p = Path(relative)
        if p.is_absolute() or win.drive or win.is_absolute() or ".." in p.parts or ":" in relative:
            raise ReferenceError(f"Unsafe project path: {relative}")
        result = (self.root / p).resolve()
        if not result.is_relative_to(self.root):
            raise ReferenceError(f"Path escapes project root: {relative}")
        if exists and not result.is_file():
            raise ReferenceError(f"Missing project input: {relative}")
        return result

    def generated(self, kind, *, check=True):
        value = read_json(self.path(self.data["generated"][kind], exists=True))
        if check:
            validate(value, kind)
        if kind == 'cage' and value.get('schema_version') == 2:
            from ..authoring.contracts import resolved_cage
            value = resolved_cage(value)
        return value

    @property
    def blend(self):
        return self.path(f"output/{self.data['asset_name']}.blend")

    @property
    def glb(self):
        return self.path(f"output/{self.data['asset_name']}.glb")
