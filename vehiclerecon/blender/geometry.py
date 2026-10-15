"""Primitive Blender adapters. Coordinates/names/material IDs belong to data."""
import bpy
from .collections import ensure

def mesh(name, vertices, faces, material, collection):
    data = bpy.data.meshes.new(name)
    data.from_pydata([tuple(v) for v in vertices], [], faces)
    data.update()
    obj = bpy.data.objects.new(name,data)
    ensure(collection).objects.link(obj)
    if material:
        data.materials.append(bpy.data.materials[material] if isinstance(material,str) else material)
    for face in data.polygons:
        face.use_smooth = True
    return obj

def curve(name, points, material, radius, collection, cyclic=False, handles='AUTO'):
    data = bpy.data.curves.new(name,'CURVE')
    data.dimensions = '3D'
    data.resolution_u = 16
    data.bevel_depth = radius
    data.bevel_resolution = 2
    sp = data.splines.new('BEZIER')
    sp.bezier_points.add(len(points)-1)
    sp.use_cyclic_u = cyclic
    for point,position in zip(sp.bezier_points,points):
        point.co = position
        point.handle_left_type = handles
        point.handle_right_type = handles
    obj = bpy.data.objects.new(name,data)
    ensure(collection).objects.link(obj)
    if material:
        data.materials.append(bpy.data.materials[material])
    return obj
