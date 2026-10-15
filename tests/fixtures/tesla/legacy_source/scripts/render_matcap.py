"""Workbench reflective matcap from the real model, without topology overlay."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project import *
visibility={ob.name:ob.hide_render for ob in bpy.data.objects}
for ob in bpy.data.objects:
    if ob.name.startswith(('WIRE_','CAGE_','REF_')) or ob.name=='STUDIO_GROUND':ob.hide_render=True
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH'
s.display.shading.light='MATCAP';s.display.shading.studio_light='metal_carpaint.exr'
s.display.shading.color_type='SINGLE';s.display.shading.single_color=(.65,.65,.65)
s.display.shading.show_shadows=False;s.display.shading.show_cavity=False
s.display.shading.background_type='WORLD'
render('validation/surface_matcap.png','CAM_3Q',1600,1000)
for name,hidden in visibility.items():
    if name in bpy.data.objects:bpy.data.objects[name].hide_render=hidden
print('ACTUAL_WORKBENCH_REFLECTION_MATCAP_RENDERED')
