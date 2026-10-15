import bpy
from mathutils import Vector
from .collections import ensure

def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()

def camera(config, collection):
    name = config['name']
    obj = bpy.data.objects.get(name)
    if obj is None:
        obj = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        ensure(collection).objects.link(obj)
    obj.data.type = config.get('type', 'ORTHO')
    obj.data.ortho_scale = config['scale']
    obj.location = config['position']
    aim(obj, config['target'])
    obj['calibrated'] = True
    return obj
