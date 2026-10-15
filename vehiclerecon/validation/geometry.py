"""Pure geometry acceptance policy; the Blender audit is read-only."""
from ..core.errors import GateError

def require_audit(report):
    if report['status']!='PASS' or not report['finite_and_nonzero_faces']:
        raise GateError('Geometry audit failed')
    if not report['wheel_pivots_pass']:
        raise GateError('Wheel pivot alignment failed')
    if not report.get('semantic_roles_pass',False):
        raise GateError('Semantic role bindings failed')
    if not report.get('metric_units',False):
        raise GateError('Scene units must be metric with unit scale')

def validate_roles(profile,bindings,available):
    missing_roles=sorted(set(profile['roles'])-set(bindings))
    missing_objects=sorted({name for names in bindings.values() for name in names if name not in available})
    empty_roles=sorted(role for role,names in bindings.items() if not names)
    return {'pass':not (missing_roles or missing_objects or empty_roles),'missing_roles':missing_roles,
            'missing_objects':missing_objects,'empty_roles':empty_roles}
