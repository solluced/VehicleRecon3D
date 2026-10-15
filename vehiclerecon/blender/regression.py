"""Read-only comparison to an explicitly supplied frozen Blender fixture."""
import bpy,math
from ..core.errors import GateError
from ..core.manifest import write_json,digest_file
from .audit import model_objects

def snapshot(project):
    result={}
    for obj in model_objects(project):
        record={'type':obj.type,'parent':obj.parent.name if obj.parent else None,
                'matrix':[list(r) for r in obj.matrix_world]}
        if obj.type=='MESH':
            record['vertices']=[list(v.co) for v in obj.data.vertices]
            record['faces']=[list(f.vertices) for f in obj.data.polygons]
        elif obj.type=='CURVE':
            record['points']=[[list(p.co),list(p.handle_left),list(p.handle_right)] for sp in obj.data.splines for p in sp.bezier_points]
        result[obj.name]=record
    collection=project.generated('cage',check=False)['collection']
    cage={obj.name:[{'cyclic':sp.use_cyclic_u,'points':[[list(p.co),list(p.handle_left),list(p.handle_right)] for p in sp.bezier_points]} for sp in obj.data.splines]
          for obj in bpy.data.collections[collection].objects}
    return {'objects':result,'cage':cage,'units':[bpy.context.scene.unit_settings.system,bpy.context.scene.unit_settings.scale_length]}

def coordinate_error(a,b):
    if isinstance(a,(list,tuple)):
        if not isinstance(b,(list,tuple)) or len(a)!=len(b):return float('inf')
        return max((coordinate_error(x,y) for x,y in zip(a,b)),default=0)
    return abs(a-b)

def compare(project,baseline):
    current=snapshot(project);current_hash=digest_file(project.blend);baseline_hash=digest_file(baseline)
    bpy.ops.wm.open_mainfile(filepath=str(baseline));expected=snapshot(project)
    same_names=set(current['objects'])==set(expected['objects']);checks=[]
    for name,source in expected['objects'].items():
        actual=current['objects'].get(name)
        if not actual:
            checks.append({'object':name,'pass':False,'reason':'missing'});continue
        topology=source.get('faces')==actual.get('faces')
        positions=coordinate_error(source.get('vertices',source.get('points',[])),actual.get('vertices',actual.get('points',[])))
        matrix_error=coordinate_error(source['matrix'],actual['matrix'])
        structure=source['type']==actual['type'] and source['parent']==actual['parent']
        checks.append({'object':name,'pass':topology and positions<1e-5 and matrix_error<1e-6 and structure,
                       'same_control_topology':topology,'max_control_coordinate_error_m':positions if math.isfinite(positions) else None,
                       'max_matrix_error':matrix_error if math.isfinite(matrix_error) else None,'same_structure':structure})
    cage_match=current['cage']==expected['cage']
    passed=same_names and cage_match and current['units']==expected['units'] and all(c['pass'] for c in checks)
    report={'status':'PASS' if passed else 'FAIL','source_blend_sha256':current_hash,'baseline_blend_sha256':baseline_hash,
            'physical_object_names_match':same_names,'cage_count':len(current['cage']),'cage_controls_handles_exact':cage_match,
            'units_match':current['units']==expected['units'],'max_control_coordinate_error_m':max((c['max_control_coordinate_error_m'] for c in checks if c.get('max_control_coordinate_error_m') is not None),default=0),
            'control_coordinate_tolerance_m':1e-5,'objects':checks,'method':'Read-only local control vertices, connectivity, transforms, parents and Bezier handles; diagnostic topology overlays excluded.'}
    write_json(project.path('validation/control_regression.json'),report)
    if digest_file(project.blend)!=current_hash or digest_file(baseline)!=baseline_hash:raise GateError('Regression inspection modified a Blender source')
    if not passed:raise GateError('Frozen Blender control/structure regression failed')
