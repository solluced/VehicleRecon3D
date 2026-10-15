"""Seat the rear lamp returns on the actual refined hatch surface."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project import *
from mathutils.bvhtree import BVHTree
target=bpy.data.objects['REAR_HATCH'];deps=bpy.context.evaluated_depsgraph_get()
tree=BVHTree.FromObject(target,deps)
for label in ('L','R'):
    housing=bpy.data.objects['TAIL_RETURN_HOUSING_'+label];lens=bpy.data.objects['TAIL_RETURN_LENS_'+label]
    for black,red in zip(housing.data.splines[0].bezier_points,lens.data.splines[0].bezier_points):
        point=target.matrix_world.inverted()@(housing.matrix_world@black.co)
        location,normal,index,distance=tree.find_nearest(point)
        world=target.matrix_world@location
        n=(target.matrix_world.to_3x3().inverted().transposed()@normal).normalized()
        black.co=housing.matrix_world.inverted()@(world+n*.002)
        red.co=lens.matrix_world.inverted()@(world+n*.010)
bpy.context.view_layer.update();save()
print('REAR_LAMP_RETURNS_SEATED_ON_REFINED_HATCH')
