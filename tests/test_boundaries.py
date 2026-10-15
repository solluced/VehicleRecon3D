import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_only_adapters_import_blender():
    for path in (ROOT/'vehiclerecon').rglob('*.py'):
        if 'blender' in path.relative_to(ROOT/'vehiclerecon').parts:continue
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or ''] if isinstance(node,ast.ImportFrom) else []
            assert all(name.split('.')[0] not in ('bpy','bmesh','mathutils') for name in names),path

def test_no_executable_project_files():
    assert not list((ROOT/'projects').rglob('*.py'))

def test_no_production_asserts_or_eval():
    for path in (ROOT/'vehiclerecon').rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            assert not isinstance(node,ast.Assert),path
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
                assert node.func.id not in ('eval','exec'),path
