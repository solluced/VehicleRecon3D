from ..core.errors import SchemaError

def reflected(points,axis=1):
    if axis not in (0,1,2):raise SchemaError('Invalid symmetry axis')
    return [tuple(-x if i==axis else x for i,x in enumerate(p)) for p in points]
