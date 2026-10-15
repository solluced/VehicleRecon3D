"""Audit actual model geometry and save reproducible topology/scale evidence.

Removes coincident corner vertices on small frame caps, never retopologizes
or substitutes a dense shell. Does not assert an automatic Class-A pass.
"""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project import *
import bmesh, numpy as np
cleaned=[]; seen=set()
for ob in bpy.data.objects:
    if ob.type!='MESH' or ob.name.startswith(('WIRE_','REF_')) or ob.name=='STUDIO_GROUND':continue
    if ob.data.as_pointer() in seen:continue
    seen.add(ob.data.as_pointer())
    bm=bmesh.new();bm.from_mesh(ob.data);before=(len(bm.verts),len(bm.faces))
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    zero=[f for f in bm.faces if f.calc_area()<1e-12]
    if zero:bmesh.ops.delete(bm,geom=zero,context='FACES')
    after=(len(bm.verts),len(bm.faces))
    if before!=after:
        bm.to_mesh(ob.data);ob.data.update();cleaned.append({'object':ob.name,'before':before,'after':after})
    bm.free()
surface_objects=[];vertices=0;faces=0;quads=0;bad=0
for col in ('03_BODY','04_PANELS','05_GLASS'):
    for ob in coll(col).objects:
        if ob.type!='MESH' or ob.name.startswith(('WIRE_','INNER_','MIRROR_','WHEELHOUSE')):continue
        v=len(ob.data.vertices);f=len(ob.data.polygons);q=sum(len(p.vertices)==4 for p in ob.data.polygons)
        finite=all(math.isfinite(n) for p in ob.data.vertices for n in p.co)
        invalid=sum(p.area<1e-12 for p in ob.data.polygons)
        vertices+=v;faces+=f;quads+=q;bad+=invalid+int(not finite)
        surface_objects.append({'name':ob.name,'vertices':v,'faces':f,'quads':q,'finite':finite,'zero_area_faces':invalid,'modifiers':[m.type for m in ob.modifiers]})
deps=bpy.context.evaluated_depsgraph_get();bounds=[]
for col in ('03_BODY','04_PANELS','05_GLASS'):
    for ob in coll(col).objects:
        if ob.type!='MESH' or ob.name.startswith(('WIRE_','INNER_','MIRROR_','WHEELHOUSE')):continue
        ev=ob.evaluated_get(deps)
        bounds.extend([ev.matrix_world@Vector(corner) for corner in ev.bound_box])
a=np.array(bounds);lo=a.min(axis=0);hi=a.max(axis=0)
axles={name:list(bpy.data.objects[name].location) for name in ('WHEEL_FL','WHEEL_FR','WHEEL_RL','WHEEL_RR')}
evidence={'status':'geometry_checks_pass' if bad==0 else 'geometry_checks_fail','finite_and_nonzero_faces':bad==0,
    'surface_control_mesh':{'vertices':vertices,'faces':faces,'quads':quads,'quad_percent':100*quads/max(1,faces)},
    'evaluated_envelope_excludes_mirrors_wheels_display_overlays':{'min':lo.tolist(),'max':hi.tolist(),'size':(hi-lo).tolist()},
    'wheel_root_centers_m':axles,'wheelbase_m':axles['WHEEL_RL'][0]-axles['WHEEL_FL'][0],
    'cleaned_corner_vertices':cleaned,'objects':surface_objects,
    'surface_quality_note':'Topology/finite-coordinate checks do not certify curvature continuity; inspect surface_reflections.png and surface-only renders.',
    'wire_method':'Duplicate actual quad control-mesh edges, follow refined source surface, Wireframe modifier. No independent decorative grid.'}
(ROOT/'validation/geometry_audit.json').write_text(json.dumps(evidence,indent=2))
save();print(json.dumps({k:evidence[k] for k in ('status','surface_control_mesh','wheelbase_m')},indent=2))
