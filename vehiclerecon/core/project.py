"""Validated project loading without Blender imports or vehicle constants."""
import json
import math
from pathlib import Path, PureWindowsPath
from .errors import SchemaError, ReferenceError

REPOSITORY = Path(__file__).resolve().parents[2]


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


def validate(value, schema_name):
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    schema_root = REPOSITORY / "schemas"
    schemas = [read_json(p) for p in sorted(schema_root.glob("*.schema.json"))]
    registry = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in schemas)
    schema = read_json(schema_root / f"{schema_name}.schema.json")
    finite(value)
    errors = sorted(Draft202012Validator(schema, registry=registry).iter_errors(value),
                    key=lambda e: str(list(e.path)))
    if errors:
        raise SchemaError("; ".join(f"{'/'.join(map(str,e.path))}: {e.message}" for e in errors))


class Project:
    def __init__(self, root, *, check=True):
        self.root = Path(root).resolve()
        self.data = read_json(self.root / "project.json")
        if self.data.get("schema_version") != 1:
            raise SchemaError("Unsupported project schema_version")
        if check:
            validate(self.data, "project")
        for name, value in self.data.get("dimensions", {}).items():
            if name.endswith("_m") and (not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0):
                raise SchemaError(f"Dimension must be positive: {name}")
        self.profile = read_json(REPOSITORY / "profiles" / f"{self.data['vehicle_profile']}.json")
        if check:
            validate(self.profile, "vehicle_profile")
        for path in self.data["references"].values():
            self.path(path, exists=True)
        for path in self.data.get("generated", {}).values():
            self.path(path, exists=True)
        for folder in ("input", "generated", "validation", "output", ".cache"):
            self.path(folder).mkdir(exist_ok=True)

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
        return value

    @property
    def blend(self):
        return self.path(f"output/{self.data['asset_name']}.blend")

    @property
    def glb(self):
        return self.path(f"output/{self.data['asset_name']}.glb")
