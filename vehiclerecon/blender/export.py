import bpy
from ..core.errors import GateError
from ..core.project import read_json
from ..core.manifest import digest_file,write_json
from ..validation.report import review,model_inputs_hash
from ..validation.geometry import require_audit
from ..validation.silhouette import require
from .audit import geometry_hash,model_objects

def group(obj,config):
    ancestor=obj
    while ancestor.parent:ancestor=ancestor.parent
    for rule in config['group_rules']:
        if rule.get('property') and obj.get(rule['property']):return rule['group']
        if rule.get('name_prefixes') and obj.name.startswith(tuple(rule['name_prefixes'])):return rule['group']
        if rule.get('ancestor_prefixes') and ancestor.name.startswith(tuple(rule['ancestor_prefixes'])):return rule['group']
    return config['default_group']

def export(project):
    audit=read_json(project.path('validation/geometry_audit.json',exists=True));require_audit(audit)
    actual=geometry_hash(project)
    if actual!=audit['geometry_hash']:raise GateError('Geometry changed since read-only audit')
    review(project,actual,check_schema=False)
    masks=read_json(project.path('validation/final_migration_report.json',exists=True))
    require(masks['views'],project.data['validation']['baseline_iou'],project.data['validation']['max_iou_regression'])
    blend_hash=digest_file(project.blend)
    if masks['source_blend_sha256']!=blend_hash:raise GateError('Final silhouette report is stale')
    if masks.get('input_state_hash')!=model_inputs_hash(project):raise GateError('Final silhouette inputs changed')
    bpy.ops.object.select_all(action='DESELECT')
    curves=[o for o in model_objects(project,True) if o.type=='CURVE']
    if curves:
        for obj in curves:obj.hide_set(False);obj.select_set(True)
        bpy.context.view_layer.objects.active=curves[0];bpy.ops.object.convert(target='MESH')
    bpy.ops.object.select_all(action='DESELECT');source={};deps=bpy.context.evaluated_depsgraph_get()
    for obj in model_objects(project,True):
        if obj.type not in ('MESH','EMPTY'):continue
        obj.hide_set(False);obj.select_set(True);obj['viewer_group']=group(obj,project.data['export'])
        if obj.type=='MESH':
            ev=obj.evaluated_get(deps);data=ev.to_mesh();data.calc_loop_triangles()
            points=[ev.matrix_world@v.co for v in data.vertices];points=[(p.x,p.z,-p.y) for p in points]
            source[obj.name]={'triangles':len(data.loop_triangles),'bounds_min':[min(p[i] for p in points) for i in range(3)],'bounds_max':[max(p[i] for p in points) for i in range(3)]}
            ev.to_mesh_clear()
    bpy.ops.export_scene.gltf(filepath=str(project.glb),export_format='GLB',use_selection=True,export_apply=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False)
    write_json(project.path('output/export_manifest.json'),{'source_blend_sha256':blend_hash,'geometry_hash':actual,'input_state_hash':model_inputs_hash(project),
               'glb_sha256':digest_file(project.glb),'size_bytes':project.glb.stat().st_size,'source_geometry':source,
               'method':'Direct evaluated Blender export; only in-memory curve conversion; no procedural viewer model'})
