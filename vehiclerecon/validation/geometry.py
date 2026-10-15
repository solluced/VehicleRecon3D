"""Pure geometry acceptance policy; the Blender audit is read-only."""
from ..core.errors import GateError

def require_audit(report):
    if report['status']!='PASS' or not report['finite_and_nonzero_faces']:
        raise GateError('Geometry audit failed')
    if not report['wheel_pivots_pass']:
        raise GateError('Wheel pivot alignment failed')
