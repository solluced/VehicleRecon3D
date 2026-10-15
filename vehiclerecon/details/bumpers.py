from ..core.errors import SchemaError

def fins(offsets,center):
    if len(center)!=3:raise SchemaError('Invalid fin center')
    return [(center[0],offset,center[2]) for offset in offsets]
