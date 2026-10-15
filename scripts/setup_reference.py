"""Create an explicitly UNCALIBRATED Blender starter; never generate a body.

Run with Blender --background --factory-startup --python scripts/setup_reference.py
Only intended for the initial empty workspace. Refuses to overwrite a .blend.
Reference planes, camera scales and dimensions require the missing source images.
"""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'tesla_surface_model.blend'
if OUTPUT.exists():
    raise RuntimeError(f'Refusing to overwrite existing project: {OUTPUT}')

for folder in ('refs', 'docs', 'scripts', 'validation', 'exports'):
    (ROOT / folder).mkdir(exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = 'SCENE_PRESENTATION'
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene['reference_calibration'] = 'FAIL_MISSING_REFERENCE_IMAGES'
scene['cage_status'] = 'NOT_STARTED'
scene['model_status'] = 'STARTER_ONLY_NO_VEHICLE_GEOMETRY'
scene['axis_convention'] = 'X longitudinal; front -X; Y lateral; Z up; ground Z=0'
scene['camera_status'] = 'PROVISIONAL: orientations only; scales and framing uncalibrated'

for name in (
    '00_REFERENCE', '01_CURVE_CAGE', '02_BLOCKOUT', '03_BODY',
    '04_PANELS', '05_GLASS', '06_LIGHTS', '07_WHEELS',
    '08_INTERIOR', '09_PRESENTATION',
):
    scene.collection.children.link(bpy.data.collections.new(name))

def camera(name, location, target, kind='ORTHO'):
    data = bpy.data.cameras.new(name)
    data.type = kind
    data.ortho_scale = 6.0  # display placeholder, not a measured dimension
    obj = bpy.data.objects.new(name, data)
    scene.collection.children['09_PRESENTATION'].objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    obj['calibrated'] = False
    return obj

camera('CAM_FRONT', (-9, 0, 0), (0, 0, 0))
camera('CAM_REAR', (9, 0, 0), (0, 0, 0))
camera('CAM_SIDE', (0, -9, 0), (0, 0, 0))
camera('CAM_TOP', (0, 0, 9), (0, 0, 0))
scene.camera = camera('CAM_3Q', (-7, -7, 4), (0, 0, 0.7), 'PERSP')

def material(name, color, roughness, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    return mat

material('MAT_BODY_SURFACE', (0.8, 0.82, 0.84), 0.3, 0.15)
glass = material('MAT_GLASS', (0.06, 0.07, 0.08), 0.12)
glass.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value = 0.9
material('MAT_WIREFRAME', (0.015, 0.22, 0.8), 0.35)
material('MAT_TIRE', (0.018, 0.02, 0.023), 0.7)
material('MAT_RIM', (0.12, 0.14, 0.16), 0.25, 0.85)
material('MAT_LIGHT_FRONT', (0.85, 0.9, 1.0), 0.18)
material('MAT_LIGHT_REAR', (0.65, 0.015, 0.01), 0.18)

world = bpy.data.worlds.new('WORLD_STUDIO')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.8, 0.8, 0.8, 1)
scene.world = world
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100

notes = bpy.data.texts.new('READ_ME_FIRST')
notes.write('STARTER ONLY — no vehicle geometry.\n'
            'Calibration blocked: multiview, surface target, and workflow images absent.\n'
            'All cameras are uncalibrated orientation placeholders.\n'
            'Do not model until the supplied references are inspected and aligned.\n'
            'See docs/reference_dimensions.md and docs/validation_summary.md.\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT))
print('STARTER_SAVED: no geometry; calibration blocked by missing images')
