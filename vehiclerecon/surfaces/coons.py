from .curves import Vector
from ..core.errors import SchemaError

def coons(bottom,top,left=None,right=None,corner_tolerance=1e-6):
    a,b,c,d=bottom(0),bottom(1),top(0),top(1)
    left=left or (lambda v:a.lerp(c,v))
    right=right or (lambda v:b.lerp(d,v))
    error=max((left(0)-a).length,(left(1)-c).length,(right(0)-b).length,(right(1)-d).length)
    if error>corner_tolerance:
        raise SchemaError(f'Coons corners disagree by {error}m (allowed {corner_tolerance})')
    def sample(u,v):
        return bottom(u)*(1-v)+top(u)*v+left(v)*(1-u)+right(v)*u-((1-u)*(1-v)*a+u*(1-v)*b+(1-u)*v*c+u*v*d)
    return sample

def bilinear_patch(points,vector=Vector):
    if len(points)!=4:raise SchemaError('Bilinear patch needs four corners')
    a,b,c,d=map(vector,points)
    return lambda u,v:a*(1-u)*(1-v)+b*u*(1-v)+c*u*v+d*(1-u)*v
