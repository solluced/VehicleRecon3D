"""Shared Blender scene utilities; dimensions are measured in reference_data.json."""
from pathlib import Path
import bpy, json, math
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'refs/reference_data.json').read_text())
L = DATA['scale']['length_m']
S = L / 733
W = DATA['scale']['width_m']
H = DATA['scale']['height_m']
def sx(u): return (u - 761.5) * S
def sz(v): return (741 - v) * S
def ty(v): return (932 - v) * W / 280
def tx(u): return (u - 760) * L / 714
def coll(name): return bpy.data.collections[name]
def move(obj, collection):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    coll(collection).objects.link(obj)
    return obj
def aim(obj, target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
def camera(name, pos, target, scale=5.7):
    obj=bpy.data.objects.get(name)
    if obj is None:
        obj=bpy.data.objects.new(name,bpy.data.cameras.new(name)); coll('09_PRESENTATION').objects.link(obj)
    obj.data.type='ORTHO'; obj.data.ortho_scale=scale; obj.location=pos; aim(obj,target)
    obj['calibrated']=True
    return obj
def mat(name,color,roughness=.3,metallic=0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes=True; p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=roughness
    p.inputs['Metallic'].default_value=metallic
    m.diffuse_color=(*color,1); m.use_fake_user=True
    return m
def emissive(name,color):
    m=bpy.data.materials.new(name); m.use_nodes=True
    n=m.node_tree.nodes; n.clear(); e=n.new('ShaderNodeEmission'); e.inputs[0].default_value=(*color,1)
    o=n.new('ShaderNodeOutputMaterial'); m.node_tree.links.new(e.outputs[0],o.inputs[0]); return m
def curve(name, points, material=None, radius=.003, collection='01_CURVE_CAGE', cyclic=False, handles='AUTO'):
    data=bpy.data.curves.new(name,'CURVE'); data.dimensions='3D'; data.resolution_u=16; data.bevel_depth=radius; data.bevel_resolution=2
    sp=data.splines.new('BEZIER'); sp.bezier_points.add(len(points)-1); sp.use_cyclic_u=cyclic
    for b,p in zip(sp.bezier_points,points):
        b.co=p; b.handle_left_type=handles; b.handle_right_type=handles
    obj=bpy.data.objects.new(name,data); coll(collection).objects.link(obj)
    if material: data.materials.append(material)
    return obj
def mesh(name,verts,faces,material,collection):
    data=bpy.data.meshes.new(name); data.from_pydata(verts,[],faces); data.update()
    ob=bpy.data.objects.new(name,data); coll(collection).objects.link(ob)
    if material: data.materials.append(material)
    for p in data.polygons: p.use_smooth=True
    return ob
def save():
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'tesla_surface_model.blend'))
def render(path,camera_name,width=1200,height=800):
    s=bpy.context.scene; s.camera=bpy.data.objects[camera_name]; s.render.resolution_x=width; s.render.resolution_y=height
    s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; s.render.filepath=str(ROOT/path)
    bpy.ops.render.render(write_still=True)
