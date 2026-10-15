"""Blender execution of validated automobile component records."""
import bpy,bmesh,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from ..core.errors import GateError,ReferenceError
from ..core.project import read_json
from ..core.manifest import digest_file
from ..details.builder import check
from ..details.lights import selected,attachment_pairs
from ..details.doors import panel_gap,backing
from ..details.wheels import revolved,radial_spokes
from .geometry import mesh,curve
from .collections import ensure,link
from .materials import material
from .scene import save

def object_by_id(name):
    obj=bpy.data.objects.get(name)
    if obj is None:raise ReferenceError(f'Unknown component object {name}')
    return obj

def flip(data):
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()

def mirror(obj):
    mod=obj.modifiers.new('Symmetry','MIRROR');mod.use_axis[0]=False;mod.use_axis[1]=True

def split(obj,left,right):
    for mod in list(obj.modifiers):
        if mod.type=='MIRROR':obj.modifiers.remove(mod)
    obj.name=right
    other=obj.copy();other.data=obj.data.copy();ensure(obj.users_collection[0].name).objects.link(other);other.name=left
    for vertex in other.data.vertices:vertex.co.y*=-1
    flip(other.data)
    return other,obj

def box(config):
    bpy.ops.mesh.primitive_cube_add(size=1,location=config['position'])
    obj=bpy.context.object;obj.name=config['name'];obj.scale=config['size']
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    link(obj,config['collection']);obj.data.materials.append(bpy.data.materials[config['material']])
    for face in obj.data.polygons:face.use_smooth=True
    if config['bevel']:
        mod=obj.modifiers.new('Edge radii','BEVEL');mod.width=config['bevel'];mod.segments=config['segments']
        mod=obj.modifiers.new('Face normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    obj.rotation_euler=config['rotation']
    return obj

def cavity(config):
    obj=object_by_id(config['source']);data=obj.data
    us=list(obj['grid_us']);vs=list(obj['grid_vs']);nx=len(us)-1
    if 'patch_u' not in data.attributes:
        ua=data.attributes.new('patch_u','FLOAT','FACE');va=data.attributes.new('patch_v','FLOAT','FACE')
        for face in data.polygons:
            j,i=divmod(face.index,nx)
            ua.data[face.index].value=(us[i]+us[i+1])/2;va.data[face.index].value=(vs[j]+vs[j+1])/2
    ua=data.attributes['patch_u'].data;va=data.attributes['patch_v'].data
    indices=[f.index for f in data.polygons if selected(ua[f.index].value,va[f.index].value,config['selection'])]
    if not indices:raise GateError(f"Empty aperture selection {config['name']}")
    used=sorted({v for i in indices for v in data.polygons[i].vertices});remap={old:new for new,old in enumerate(used)}
    vertices=[data.vertices[i].co+Vector(config['offset']) for i in used]
    faces=[tuple(remap[v] for v in data.polygons[i].vertices) for i in indices]
    housing=mesh(config['name'],vertices,faces,config['material'],config['collection'])
    mod=housing.modifiers.new('Detail smoothing','SUBSURF');mod.levels=config['smoothing'];mod.render_levels=config['smoothing']
    mod=housing.modifiers.new('Recessed lens thickness','SOLIDIFY');mod.thickness=config['thickness']
    if config['symmetric']:mirror(housing)
    bm=bmesh.new();bm.from_mesh(data);bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.faces[i] for i in indices],context='FACES')
    crease=bm.edges.layers.float.get('crease_edge') or bm.edges.layers.float.new('crease_edge')
    for edge in bm.edges:
        if edge.is_boundary:edge[crease]=config['crease']
    bm.to_mesh(data);bm.free();data.update()
    return housing

def cylinder(name,radius,depth,location,material_id,parent,segments,collection):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=radius,depth=depth,location=location,rotation=(math.pi/2,0,0))
    obj=bpy.context.object;obj.name=name;link(obj,collection);obj.data.materials.append(bpy.data.materials[material_id]);obj.parent=parent
    for face in obj.data.polygons:face.use_smooth=True
    return obj

def wheels(project,config):
    blockout=project.generated('surface_graph',check=False)['blockout']
    axles={a['id']:a for a in project.generated('calibration',check=False)['wheel_geometry']['axles']}
    for binding in blockout['wheels']:
        label=binding['label'];side=binding['side'];fmt={'label':label}
        tire=object_by_id(config['tire_name'].format(**fmt));center=tire.location.copy();tire.name=config['renamed_tire'].format(**fmt)
        root=bpy.data.objects.new(config['root_name'].format(**fmt),None);ensure(config['collection']).objects.link(root);root.location=center
        tire.parent=root;tire.location=(0,0,0)
        disc=object_by_id(config['disc_name'].format(**fmt));disc.name=config['brake_name'].format(**fmt);disc.parent=root;disc.location=(0,0,0)
        disc.data=disc.data.copy();disc.data.materials.clear();disc.data.materials.append(bpy.data.materials[config['brake_material']])
        for vertex in disc.data.vertices:vertex.co.y=side*config['brake_depth']
        vertices,faces=revolved([(r,side*y) for r,y in config['rim_profile']],config['rim_segments'])
        rim=mesh(config['rim_name'].format(**fmt),vertices,faces,config['rim_material'],config['collection']);rim.parent=root
        for i,polygon in enumerate(radial_spokes(config['spoke_polygon'],config['spoke_count'],config['spoke_depth'],side)):
            blade=mesh(config['spoke_name'].format(**fmt,index=i+1),polygon,[tuple(range(len(polygon)))],config['spoke_material'],config['collection']);blade.parent=root
            if blade.data.polygons[0].normal.y*side<0:flip(blade.data)
            mod=blade.modifiers.new('Spoke depth','SOLIDIFY');mod.thickness=config['spoke_thickness']
            mod=blade.modifiers.new('Spoke radii','BEVEL');mod.width=config['spoke_bevel'];mod.segments=config['spoke_bevel_segments']
            blade.modifiers.new('Spoke normals','WEIGHTED_NORMAL')
        for role,material_id in [('hub',config['hub_material']),('cap',config['cap_material'])]:
            item=config[role]
            cylinder(config[role+'_name'].format(**fmt),item['radius'],item['depth'],(0,side*item['offset'],0),material_id,root,config['cylinder_segments'],config['collection'])
        lug=config['lug']
        for i in range(lug['count']):
            angle=i*math.tau/lug['count']
            cylinder(config['lug_name'].format(**fmt),lug['radius'],lug['depth'],(lug['bolt_circle_radius']*math.cos(angle),side*lug['offset'],lug['bolt_circle_radius']*math.sin(angle)),config['cap_material'],root,config['cylinder_segments'],config['collection'])

def attach(config):
    target=object_by_id(config['target']);deps=bpy.context.evaluated_depsgraph_get();tree=BVHTree.FromObject(target,deps)
    pairs=[(object_by_id(name),offset) for name,offset in attachment_pairs(config)]
    cardinalities={len(obj.data.splines[0].bezier_points) for obj,offset in pairs}
    if len(cardinalities)!=1:raise GateError('Paired attachment curve cardinalities differ')
    # The first boundary supplies the common nearest-surface sample, preserving alignment.
    anchor=pairs[0][0]
    for i,point in enumerate(anchor.data.splines[0].bezier_points):
        local=target.matrix_world.inverted()@(anchor.matrix_world@point.co)
        location,normal,index,distance=tree.find_nearest(local)
        if location is None:raise GateError('Surface attachment has no nearest point')
        world=target.matrix_world@location;n=(target.matrix_world.to_3x3().inverted().transposed()@normal).normalized()
        for obj,offset in pairs:obj.data.splines[0].bezier_points[i].co=obj.matrix_world.inverted()@(world+n*offset)
    bpy.context.view_layer.update()

def execute(project,config):
    op=config['operation']
    if op=='box':return box(config)
    if op=='curve':return curve(config['name'],config['points'],config['material'],config['radius'],config['collection'],config['cyclic'],config['handles'])
    if op=='cavity':return cavity(config)
    if op in ('split','door_split'):
        obj=object_by_id(config['source'])
        if op=='door_split':
            for vertex,point in zip(obj.data.vertices,panel_gap([tuple(v.co) for v in obj.data.vertices],config['gap'])):vertex.co=point
        objects=split(obj,config['left'],config['right'])
        if op=='door_split':
            for door in objects:
                skin=door.copy();skin.data=door.data.copy();ensure(door.users_collection[0].name).objects.link(skin);skin.name=config['backing_prefix']+door.name
                skin.data.materials.clear();skin.data.materials.append(bpy.data.materials[config['backing_material']])
                for vertex,point in zip(skin.data.vertices,backing([tuple(v.co) for v in skin.data.vertices],config['backing_inset'])):vertex.co=point
        return objects
    if op=='polygon':
        for name in config['remove']:bpy.data.objects.remove(object_by_id(name),do_unlink=True)
        obj=mesh(config['name'],config['points'],config['faces'],config['material'],config['collection'])
        if config['mirror']:mirror(obj)
        mod=obj.modifiers.new('Pillar thickness','SOLIDIFY');mod.thickness=config['thickness']
        mod=obj.modifiers.new('Pillar edge radius','BEVEL');mod.width=config['bevel'];mod.segments=config['segments']
        return obj
    if op=='wheels':return wheels(project,config)
    if op=='torus':
        bpy.ops.mesh.primitive_torus_add(major_radius=config['major_radius'],minor_radius=config['minor_radius'],major_segments=config['major_segments'],minor_segments=config['minor_segments'],location=config['position'],rotation=config['rotation'])
        obj=bpy.context.object;obj.name=config['name'];link(obj,config['collection']);obj.data.materials.append(bpy.data.materials[config['material']]);return obj
    if op=='assembly':
        root=bpy.data.objects.new(config['name'],None);ensure(config['collection']).objects.link(root)
        for collection in config['member_collections']:
            for obj in list(ensure(collection).objects):
                if obj!=root and obj.parent is None:obj.parent=root
        return root
    if op=='attach':return attach(config)
    raise GateError(f'Unknown detail operation {op}')

def build(project):
    report=read_json(project.path('validation/surface_migration_report.json'))
    if report['status']!='PASS' or report['source_blend_sha256']!=digest_file(bpy.data.filepath):
        raise GateError('Details require a current surface silhouette PASS')
    config=project.generated('details',check=False)
    for entry in config['materials']:material(entry)
    for record in check(config):execute(project,record['parameters'])
    save(project.path('.cache/details.blend'))
