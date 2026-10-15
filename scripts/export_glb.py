"""Export only after both actual silhouette and surface quality gates pass."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project import *
report=json.loads((ROOT/'validation/report.json').read_text())
if not (report.get('silhouette_pass') and report.get('surface_quality_pass') and report.get('export_allowed')):
    raise RuntimeError('Export refused: silhouette and surface quality validation must both pass.')
source_hash=hashlib.sha256((ROOT/'tesla_surface_model.blend').read_bytes()).hexdigest()
assert report.get('source_blend_sha256')==source_hash,'Validation report belongs to a different .blend state'
review=json.loads((ROOT/'validation/surface_review.json').read_text())
assert review['status']=='PASS' and review['source_blend_sha256']==source_hash
# Convert only the visible detail curves in this in-memory export session.
# The saved Blender project retains its editable source curves unchanged.
bpy.ops.object.select_all(action='DESELECT')
curves=[ob for col in ('03_BODY','04_PANELS','05_GLASS','06_LIGHTS','07_WHEELS','08_INTERIOR') for ob in coll(col).objects if ob.type=='CURVE' and not ob.hide_render]
if curves:
    for ob in curves:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=curves[0];bpy.ops.object.convert(target='MESH')
bpy.ops.object.select_all(action='DESELECT')
source_geometry={};deps=bpy.context.evaluated_depsgraph_get()
for col in ('03_BODY','04_PANELS','05_GLASS','06_LIGHTS','07_WHEELS','08_INTERIOR'):
    for ob in coll(col).objects:
        if ob.type in ('MESH','EMPTY') and not ob.hide_render:
            ob.hide_set(False); ob.select_set(True)
            ancestor=ob
            while ancestor.parent is not None:ancestor=ancestor.parent
            ob['viewer_group']='wire' if ob.name.startswith('WIRE_') else 'wheels' if ancestor.name.startswith('WHEEL_') else 'glass' if ob.name.startswith(('GLASS_','MIRROR_GLASS_')) else 'body'
            if ob.type=='MESH':
                ev=ob.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles()
                points=[ev.matrix_world@v.co for v in me.vertices]
                points=[(v.x,v.z,-v.y) for v in points]
                low=[min(p[i] for p in points) for i in range(3)];high=[max(p[i] for p in points) for i in range(3)]
                source_geometry[ob.name]={'triangles':len(me.loop_triangles),'bounds_min':low,'bounds_max':high}
                ev.to_mesh_clear()
bpy.ops.export_scene.gltf(filepath=str(ROOT/'exports/tesla_surface_model.glb'),export_format='GLB',use_selection=True,export_apply=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False)
path=ROOT/'exports/tesla_surface_model.glb'
manifest={'source_blend_sha256':source_hash,'glb_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size_bytes':path.stat().st_size,'source_geometry':source_geometry,'geometry_source':'Direct Blender export with evaluated modifiers; detail curves converted only in memory. No independent browser geometry.'}
(ROOT/'exports/export_manifest.json').write_text(json.dumps(manifest,indent=2))
print('GLB_EXPORTED',path.stat().st_size,'bytes',len(source_geometry),'mesh objects')
