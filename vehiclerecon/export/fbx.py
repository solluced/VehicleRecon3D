"""FBX is intentionally not advertised as an implemented v0.1 capability."""
from ..core.errors import BlockedError

def export(project):
    raise BlockedError('FBX capability has not been implemented and regression-tested; use GLB')
