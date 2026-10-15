"""Reflection-stripe render from actual smoothed body geometry."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project import *
s=bpy.context.scene
visibility={ob.name:ob.hide_render for ob in bpy.data.objects}
for col in ('00_REFERENCE','01_CURVE_CAGE'):
    for ob in coll(col).objects: ob.hide_render=True
for ob in bpy.data.objects:
    if ob.name.startswith('WIRE_'):ob.hide_render=True
m=bpy.data.materials.new('MAT_REFLECTION_STRIPES'); m.use_nodes=True
n=m.node_tree.nodes; n.clear()
tex=n.new('ShaderNodeTexCoord'); wave=n.new('ShaderNodeTexWave'); wave.wave_type='BANDS'; wave.bands_direction='X'
wave.inputs['Scale'].default_value=5
ramp=n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position=.43; ramp.color_ramp.elements[1].position=.57
ramp.color_ramp.elements[0].color=(.015,.015,.015,1); ramp.color_ramp.elements[1].color=(.9,.9,.9,1)
p=n.new('ShaderNodeBsdfPrincipled'); p.inputs['Roughness'].default_value=.15; p.inputs['Metallic'].default_value=.3
out=n.new('ShaderNodeOutputMaterial')
# Reflection coordinates, rather than object-space bands, expose normal flow.
m.node_tree.links.new(tex.outputs['Reflection'],wave.inputs['Vector']); m.node_tree.links.new(wave.outputs['Color'],ramp.inputs[0])
m.node_tree.links.new(ramp.outputs[0],p.inputs['Base Color']); m.node_tree.links.new(p.outputs[0],out.inputs[0])
original={}
for col in ('03_BODY','04_PANELS','05_GLASS'):
    for ob in coll(col).objects:
        if ob.type!='MESH' or ob.name.startswith('WIRE_'):continue
        original[ob.name]=list(ob.data.materials); ob.data.materials.clear(); ob.data.materials.append(m)
s.render.engine='CYCLES'; s.cycles.samples=24
render('validation/surface_reflections.png','CAM_3Q',1600,1000)
for name,materials in original.items():
    ob=bpy.data.objects[name]; ob.data.materials.clear()
    for material in materials:ob.data.materials.append(material)
for name,value in visibility.items():
    if name in bpy.data.objects:bpy.data.objects[name].hide_render=value
print('REFLECTION_INSPECTION_RENDERED; manual surface review required')
