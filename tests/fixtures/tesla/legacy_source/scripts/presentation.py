"""Studio presentation and real evaluated mesh-edge wire overlay."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project import *

for ob in list(bpy.data.objects):
    if ob.name.startswith('WIRE_') or ob.name=='STUDIO_GROUND':bpy.data.objects.remove(ob,do_unlink=True)
for col in ('00_REFERENCE','01_CURVE_CAGE'):
    for ob in coll(col).objects: ob.hide_render=True;ob.hide_set(True)
wire=mat('MAT_WIREFRAME',(.012,.09,.42),.5)
wire.node_tree.nodes.get('Principled BSDF').inputs['Emission Color'].default_value=(.006,.04,.16,1)
wire.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=.15
glass=bpy.data.materials['MAT_GLASS'];p=glass.node_tree.nodes.get('Principled BSDF')
p.inputs['Base Color'].default_value=(.42,.47,.53,1);p.inputs['Transmission Weight'].default_value=.9;p.inputs['Metallic'].default_value=0
selected=['HOOD','FENDER_FRONT','FENDER_REAR','DOOR_FL','DOOR_FR','DOOR_RL','DOOR_RR','BUMPER_FRONT','BUMPER_REAR','REAR_HATCH','REAR_HATCH_TOP','PILLAR_C_QUARTER','PILLAR_A_FOOT','NOSE_HOOD_BRIDGE','NOSE_CHEEK','BELTLINE_LEDGE','COWL_TRANSITION','GLASS_WINDSHIELD','GLASS_ROOF','GLASS_REAR','GLASS_FRONT_LEFT','GLASS_FRONT_RIGHT','GLASS_REAR_LEFT','GLASS_REAR_RIGHT']
for name in selected:
    source=bpy.data.objects[name]
    ob=source.copy();ob.data=source.data.copy();coll('03_BODY').objects.link(ob);ob.name='WIRE_'+name
    for m in list(ob.modifiers):
        if m.type!='MIRROR':ob.modifiers.remove(m)
    ob.data.materials.clear();ob.data.materials.append(wire)
    wrap=ob.modifiers.new('Follow actual refined surface','SHRINKWRAP');wrap.target=source;wrap.wrap_method='NEAREST_SURFACEPOINT';wrap.offset=.0008
    m=ob.modifiers.new('Real mesh edge overlay','WIREFRAME');m.thickness=.0018;m.offset=1;m.use_replace=True;m.use_boundary=True
    ob['source_topology_object']=source.name
    ob['wire_method']='Actual SubD control-mesh quad edges, projected to the source refined surface'

groundmat=mat('MAT_STUDIO_GROUND',(.72,.74,.77),.65)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.012));ground=bpy.context.object;ground.name='STUDIO_GROUND';move(ground,'09_PRESENTATION');ground.data.materials.append(groundmat)
cam=camera('CAM_3Q',(-7.5,-8,3.2),(0,0,.75),5.6)
s=bpy.context.scene;s.camera=cam;s.render.engine='CYCLES';s.cycles.samples=48;s.view_settings.view_transform='AgX'
s['presentation_wire']='Real quad mesh edges; see source_topology_object on each WIRE object'
for image in bpy.data.images:
    if image.name.startswith('reference_') or image.name.startswith('REF_CROP_'):
        image.use_fake_user=True
        if image.source=='FILE':image.pack()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.overlay.show_overlays=False
            area.spaces.active.shading.color_type='MATERIAL'
bpy.data.orphans_purge(do_recursive=True)
save()
render('validation/perspective.png','CAM_3Q',1600,1000)
for ob in bpy.data.objects:
    if ob.name.startswith('WIRE_'):ob.hide_render=True
render('validation/perspective_surface.png','CAM_3Q',1600,1000)
for ob in bpy.data.objects:
    if ob.name.startswith('WIRE_'):ob.hide_render=False
print('PRESENTATION_SAVED: real topology overlay and surface-only renders')
