"""Blender collection/object helpers; IDs always come from caller data."""
import bpy

def ensure(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col

def link(obj, collection):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    ensure(collection).objects.link(obj)
    return obj

def remove_objects(collection):
    for obj in list(ensure(collection).objects):
        bpy.data.objects.remove(obj, do_unlink=True)
