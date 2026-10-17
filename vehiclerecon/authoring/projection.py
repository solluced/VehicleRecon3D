"""Pure shared calibration, individual residuals and cage feedback samples."""
import math
from ..core.errors import SchemaError
from ..reference.transforms import CalibrationTransform
from ..cage.curves import expand
from ..surfaces.curves import polyline
from .contracts import observations, world_binding, observed_pixel, resolved_cage


def project_world(calibration, view, point):
    return CalibrationTransform(calibration).world_to_pixel(view, *point)

def registered(calibration,observation):
    view=calibration['views'][observation['view']]
    if view.get('source_state')=='CALIBRATION_REQUIRED':return False
    if 'reference_id' in view:return observation['reference_id']==view['reference_id']
    return not calibration.get('source_sha256') or observation['source_sha256']==calibration['source_sha256']


def residual(observed, projected, allowed_tolerance_px):
    if not math.isfinite(allowed_tolerance_px) or allowed_tolerance_px <= 0:
        raise SchemaError('Residual tolerance must be finite and positive')
    if observed is None:
        return {'dx':None,'dy':None,'residual_px':None,'allowed_tolerance_px':allowed_tolerance_px,'status':'BLOCKED'}
    if len(observed) != 2 or len(projected) != 2 or not all(math.isfinite(x) for x in (*observed,*projected)):
        raise SchemaError('Residual coordinates must be finite pixel pairs')
    dx, dy = (a-b for a,b in zip(projected, observed));distance = math.hypot(dx,dy)
    return {'dx':dx,'dy':dy,'residual_px':distance,'allowed_tolerance_px':allowed_tolerance_px,
            'status':'PASS' if distance <= allowed_tolerance_px else 'FAIL'}


def batch_projection(calibration, cage):
    transform = CalibrationTransform(calibration);obs = observations(calibration);rows = []
    for link in calibration['correspondences']:
        observation = obs[link['observation_id']];world = world_binding(cage,link)
        projected = transform.world_to_pixel(observation['view'],*world)
        measured = observed_pixel(observation,link)
        if not registered(calibration,observation):
            measured=None  # No declared registration from a different image to this calibration.
        rows.append({'id':link['id'],'observation_id':observation['id'],'world_entity_id':link['world_entity_id'],
                     'point_id':link.get('point_id'),'view':observation['view'],'semantic_role':link['semantic_role'],
                     'required':link['required'],'observed_pixel':measured,'projected_pixel':list(projected),
                     'world':list(world),**residual(measured,projected,link['tolerance_policy']['allowed_px'])})
    return rows


def coverage(calibration):
    policy = calibration['authoring_policy'];obs = observations(calibration)
    links = {l['id']:l for l in calibration['correspondences']}
    required = policy['critical_correspondence_ids'];reasons = []
    if not policy['coverage_confirmed'] or not required:
        reasons.append('Critical coverage has not been explicitly authored/confirmed')
    for ident in required:
        if ident not in links or not links[ident]['required']:
            reasons.append('Critical correspondence missing/not required: '+ident)
        elif obs[links[ident]['observation_id']]['visibility'] in ('occluded','unobserved'):
            reasons.append('Critical observation is unavailable: '+ident)
        elif not registered(calibration,obs[links[ident]['observation_id']]):
            reasons.append('Critical observation reference is not registered to this calibration: '+ident)
    available = {obs[links[i]['observation_id']]['view'] for i in required if i in links}
    for view in policy['required_views']:
        if view not in available:reasons.append('Critical view coverage missing: '+view)
    return {'state':'BLOCKED' if reasons else 'READY','reasons':reasons,'critical_ids':required,
            'required_views':policy['required_views']}


def residual_report(calibration, cage):
    rows = batch_projection(calibration,cage);policy = coverage(calibration)
    critical = [r for r in rows if r['required'] or r['id'] in policy['critical_ids']]
    values = [r['residual_px'] for r in critical if r['residual_px'] is not None]
    status = 'FAIL' if any(r['status']=='FAIL' for r in critical) else (
        'BLOCKED' if policy['state']!='READY' or any(r['status']!='PASS' for r in critical) else 'PASS')
    return {'status':status,'rows':rows,'coverage':policy,
            'summary':{'passed':sum(r['status']=='PASS' for r in critical),'total':len(critical),
                       'max_residual_px':max(values,default=None),'mean_residual_px':sum(values)/len(values) if values else None},
            'policy':'Each required/critical check must pass individually; means never determine acceptance.'}


def sample_cage(calibration, cage, *, count=64):
    if type(count) is not int or not 2 <= count <= 4096:
        raise SchemaError('Preview sample count must be 2..4096')
    result = []
    identities={c['id']:c['id'] for c in cage['curves']}
    identities.update({c['id']+'_'+side:c['id'] for c in cage['curves'] if c['symmetry'] for side,_ in cage['sides']})
    for curve in expand(resolved_cage(cage),calibration['wheel_geometry']):
        points = curve['points'];approximate = curve['handles']=='AUTO'
        samples = points if approximate else [polyline(points)(i/(count-1)) for i in range(count)]
        result.append({'entity_id':curve['id'],'semantic_role':curve['role'],'world_samples':[list(p) for p in samples],
                       'source_entity_id':identities.get(curve['id']),
                       'cyclic':curve.get('cyclic',False),'kind':curve.get('kind','rail'),
                       'control_ids':curve.get('point_ids',[]),'control_points':[list(p) for p in points],
                       'visibility':curve.get('visibility','inferred'),'approximate':approximate,
                       'sample_kind':'control_polygon' if approximate else 'piecewise_linear',
                       'authority':'Authoring feedback only; Blender resolves final AUTO handles and surfaces.'})
    return result
