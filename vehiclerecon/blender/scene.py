import bpy
from .collections import ensure
from .materials import material
from .cameras import camera, aim

def initialize(project):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = project.data['scene']['name']
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    for name in project.data['scene']['collections']:
        ensure(name)
    world = bpy.data.worlds.new('WORLD')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = project.data['scene']['world_color']
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = project.data['scene']['world_strength']
    scene.world = world
    for config in project.data['materials']:
        material(config)
    scene.render.engine = 'CYCLES'
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    return scene

def save(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(path))

def render(path, name, width, height):
    scene = bpy.context.scene
    scene.camera = bpy.data.objects[name]
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
