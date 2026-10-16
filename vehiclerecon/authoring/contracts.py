"""Typed v2 reference observations and shared cage identities."""
import copy
from ..core.errors import SchemaError, ReferenceError
from ..core.manifest import digest_data, digest_file

VIEWS = ('front', 'side', 'rear', 'top')


def crop_identity(reference_id, crop):
    return digest_data({'reference_id': reference_id, 'crop': crop})


def observations(calibration):
    result = {}
    for view, data in calibration.get('views', {}).items():
        for field in ('observations', 'source_curves'):
            for observation in data.get('landmarks', {}).get(field, []):
                if observation['id'] in result:
                    raise SchemaError('Duplicate observation ID: '+observation['id'])
                if observation['view'] != view:
                    raise SchemaError('Observation is stored in the wrong view')
                result[observation['id']] = observation
    return result


def point_value(cage, point):
    if isinstance(point, dict):
        name = point['landmark']
        if name not in cage['landmarks']:
            raise ReferenceError('Broken named world point: '+name)
        return tuple(cage['landmarks'][name])
    return tuple(point)


def resolved_cage(cage):
    result = copy.deepcopy(cage)
    for curve in result['curves']:
        curve['points'] = [point_value(cage, p) for p in curve['points']]
    return result


def world_binding(cage, link):
    name = link['world_entity_id']
    if link['binding_type'] == 'landmark':
        if name not in cage['landmarks']:
            raise ReferenceError('Missing world landmark: '+name)
        point = cage['landmarks'][name]
    else:
        matches = [c for c in cage['curves'] if c['id'] == name]
        if len(matches) != 1:
            raise ReferenceError('Missing world curve: '+name)
        curve = matches[0]
        if link.get('point_id') not in curve['point_ids']:
            raise ReferenceError('Broken stable curve point binding')
        point = point_value(cage, curve['points'][curve['point_ids'].index(link['point_id'])])
    sign = link.get('side', 1)
    return (point[0], point[1]*sign, point[2])


def observed_pixel(observation, link):
    if observation['visibility'] in ('unobserved', 'occluded'):
        return None
    if observation['kind'] == 'point':
        return observation['pixel']
    if observation['kind'] == 'circle':
        return observation['center']
    if observation['kind'] in ('polyline', 'spline', 'axis'):
        matches = [p for p in observation['points'] if p['id'] == link.get('observation_point_id')]
        if len(matches) != 1:
            raise ReferenceError('Broken source knot binding')
        return matches[0]['pixel']
    raise ReferenceError('A measurement is not a projected pixel binding')


def semantic_check(project, calibration, cage):
    """Authoring validity, not acceptance: valid drafts can contain bad fits."""
    obs = observations(calibration)
    from ..reference.rectification import AxisRectification
    for data in calibration.get('views',{}).values():
        if 'rectification' in data:AxisRectification(data['rectification'])
    measurements = calibration.get('datums', {}).get('measurements', [])
    names = [m['id'] for m in measurements]
    if len(names) != len(set(names)):
        raise SchemaError('Duplicate measurement ID')
    roles = set(project.profile['roles']+project.profile['optional_roles']) | {'axis', 'datum', 'measurement'}
    knots = {}
    identities = {}
    for o in obs.values():
        if o['semantic_role'] not in roles:
            raise SchemaError('Unsupported observation semantic role')
        reference = o['reference_id']
        if reference not in project.data['references']:
            raise ReferenceError('Observation reference ID missing')
        if reference not in identities:
            from ..reference.panels import png_size
            path = project.path(project.data['references'][reference], exists=True)
            identities[reference] = (digest_file(path),png_size(path))
        if identities[reference][0] != o['source_sha256']:
            raise ReferenceError('Observation source identity is stale')
        pixels = ([o['pixel']] if o['kind']=='point' and o['pixel'] is not None else
                  [o['center']] if o['kind']=='circle' else [p['pixel'] for p in o.get('points',[])])
        width,height = identities[reference][1]
        if any(not (0 <= p[0] <= width and 0 <= p[1] <= height) for p in pixels):
            raise ReferenceError('Observation is outside its original source image')
        data = calibration['views'][o['view']]
        if o['crop_id'] != crop_identity(reference, data.get('crop')):
            raise ReferenceError('Observation crop identity is stale')
        if o['visibility'] == 'inferred' and o['measured']:
            raise SchemaError('Inferred observation cannot be marked measured')
        if o['kind'] == 'point' and o['visibility'] == 'observed' and o['pixel'] is None:
            raise SchemaError('Measured point location is unknown')
        if o['kind'] == 'measurement' and o['measurement_id'] not in names:
            raise ReferenceError('Measurement observation has a broken reference')
        local = [p['id'] for p in o.get('points', [])]
        if len(local) != len(set(local)):
            raise SchemaError('Repeated knot ID inside source curve')
        for knot in o.get('points', []):
            identity = (o['view'], reference, o['source_sha256'], knot)
            if knot['id'] in knots and knots[knot['id']] != identity:
                raise SchemaError('Conflicting shared source knot identity')
            knots[knot['id']] = identity
    curve_ids = [c['id'] for c in cage['curves']]
    if len(curve_ids) != len(set(curve_ids)) or set(curve_ids) & set(cage['landmarks']):
        raise SchemaError('Duplicate/conflicting world entity ID')
    world_points = {}
    for curve in cage['curves']:
        if len(curve['points']) != len(curve['point_ids']) or len(set(curve['point_ids'])) != len(curve['point_ids']):
            raise SchemaError('Stable world knot cardinality is invalid')
        for ident, point in zip(curve['point_ids'], curve['points']):
            point_value(cage, point)
            if ident in world_points and world_points[ident] != point:
                raise SchemaError('Conflicting shared world knot identity')
            world_points[ident] = point
    ids, assignments = set(), set()
    for link in calibration['correspondences']:
        if link['id'] in ids:
            raise SchemaError('Duplicate correspondence ID')
        ids.add(link['id'])
        if link['observation_id'] not in obs:
            raise ReferenceError('Missing observation ID in correspondence')
        o = obs[link['observation_id']]
        if o['view'] not in VIEWS or o['kind'] == 'measurement':
            raise ReferenceError('Unsupported view/measurement projection binding')
        if link['observation_revision'] != o['revision']:
            raise ReferenceError('Stale observation revision in correspondence')
        if link['semantic_role'] != o['semantic_role']:
            raise SchemaError('Correspondence semantic role conflicts with observation')
        key = (o['id'], link.get('observation_point_id'))
        if key in assignments:
            raise SchemaError('Duplicate/conflicting observation assignment')
        assignments.add(key)
        world_binding(cage, link)
        observed_pixel(o, link)
    policy = calibration['authoring_policy']
    if len(set(policy['critical_correspondence_ids'])) != len(policy['critical_correspondence_ids']):
        raise SchemaError('Duplicate critical correspondence ID')
    if set(policy['critical_correspondence_ids'])-ids:
        raise ReferenceError('Critical correspondence is missing')
