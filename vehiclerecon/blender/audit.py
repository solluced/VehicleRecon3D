"""Explicit cleanup and separate non-mutating geometry inspection."""
import bpy,bmesh,math
import numpy as np
from mathutils import Vector
from ..core.errors import GateError
from ..core.manifest import digest_data,write_json,digest_file
from ..validation.geometry import require_audit
from .scene import save

def model_objects(project,include_wire=False):
    for collection in project.data['export']['collections']:
        for obj in bpy.data.collections[collection].objects:
            if not include_wire and obj.get('source_topology_object'):continue
            if not obj.hide_render:yield obj

def geometry_hash(project):
    deps=bpy.context.evaluated_depsgraph_get();rows=[]
    for obj in sorted(model_objects(project),key=lambda o:o.name):
        row={'name':obj.name,'type':obj.type,'parent':obj.parent.name if obj.parent else None,
             'matrix':[list(r) for r in obj.matrix_world]}
        if obj.type in ('MESH','CURVE'):
            ev=obj.evaluated_get(deps);data=ev.to_mesh()
            row['vertices']=[list(v.co) for v in data.vertices];row['faces']=[list(f.vertices) for f in data.polygons]
            ev.to_mesh_clear()
        rows.append(row)
    return digest_data(rows)

def cleanup(project):
    config=project.data['validation']['geometry'];changes=[];seen=set()
    for obj in model_objects(project):
        if obj.type!='MESH' or obj.data.as_pointer() in seen:continue
        seen.add(obj.data.as_pointer());bm=bmesh.new();bm.from_mesh(obj.data)
        before=[len(bm.verts),len(bm.faces)]
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=config['weld_distance_m'])
        zero=[f for f in bm.faces if f.calc_area()<config['area_epsilon']]
        if zero:bmesh.ops.delete(bm,geom=zero,context='FACES')
        after=[len(bm.verts),len(bm.faces)]
        if before!=after:
            bm.to_mesh(obj.data);obj.data.update();changes.append({'object':obj.name,'before':before,'after':after})
        bm.free()
    write_json(project.path('validation/topology_cleanup.json'),{'operation':'EXPLICIT_CLEANUP','changes':changes})
    save(project.path('.cache/cleaned.blend'))

def audit(project):
    before=geometry_hash(project);config=project.data['validation']['geometry']
    objects=[];bad=0
    for obj in model_objects(project):
        if obj.type!='MESH':continue
        finite=all(math.isfinite(n) for v in obj.data.vertices for n in v.co)
        zero=sum(f.area<config['area_epsilon'] for f in obj.data.polygons)
        bad+=zero+int(not finite)
        objects.append({'name':obj.name,'vertices':len(obj.data.vertices),'faces':len(obj.data.polygons),
                        'quads':sum(len(f.vertices)==4 for f in obj.data.polygons),'finite':finite,'zero_area_faces':zero})
    surface=[];bounds=[];deps=bpy.context.evaluated_depsgraph_get()
    for collection in config['surface_collections']:
        for obj in bpy.data.collections[collection].objects:
            if obj.type!='MESH' or obj.name.startswith(tuple(config['surface_exclude_prefixes'])):continue
            surface.append(next(v for v in objects if v['name']==obj.name))
            ev=obj.evaluated_get(deps);bounds.extend([ev.matrix_world@Vector(corner) for corner in ev.bound_box])
    array=np.array(bounds);low=array.min(axis=0);high=array.max(axis=0)
    faces=sum(o['faces'] for o in surface);quads=sum(o['quads'] for o in surface)
    data=project.generated('surface_graph',check=False)['blockout'];wheel_data=project.generated('calibration',check=False)['wheel_geometry']
    axles={a['id']:a for a in wheel_data['axles']}
    wheel_component=next(r['parameters'] for r in project.generated('details',check=False)['components'] if r['parameters']['operation']=='wheels')
    centers={};pivot_errors={}
    for binding in data['wheels']:
        name=wheel_component['root_name'].format(label=binding['label']);obj=bpy.data.objects[name];axle=axles[binding['axle']]
        actual=obj.matrix_world.translation;expected=Vector((axle['x'],binding['side']*axle['track_m']/2,axle['z']))
        centers[name]=list(actual);pivot_errors[name]=(actual-expected).length
    after=geometry_hash(project)
    if before!=after:raise GateError('Read-only audit changed geometry')
    passed=bad==0 and max(pivot_errors.values(),default=0)<=config['pivot_tolerance_m']
    report={'status':'PASS' if passed else 'FAIL','finite_and_nonzero_faces':bad==0,'geometry_hash':before,
            'audit_mutated_geometry':False,'source_blend_sha256':digest_file(bpy.data.filepath),
            'surface_control_mesh':{'vertices':sum(o['vertices'] for o in surface),'faces':faces,'quads':quads,'quad_percent':100*quads/max(1,faces)},
            'evaluated_body_envelope':{'min':low.tolist(),'max':high.tolist(),'size':(high-low).tolist()},
            'wheel_root_centers_m':centers,'wheel_pivot_errors_m':pivot_errors,'wheel_pivots_pass':passed,'objects':objects}
    write_json(project.path('validation/geometry_audit.json'),report);require_audit(report)
    return report
