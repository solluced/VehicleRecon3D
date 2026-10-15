import math
from ..core.errors import SchemaError

def panel_gap(vertices,gap):
    low=min(p[0] for p in vertices);high=max(p[0] for p in vertices);middle=(low+high)/2
    if gap<0 or high-low<=gap:raise SchemaError('Panel gap exceeds panel span')
    return [(middle+(p[0]-middle)*(1-gap/(high-low)),p[1],p[2]) for p in vertices]

def backing(vertices,inset):
    return [(p[0],p[1]-math.copysign(inset,p[1]),p[2]) for p in vertices]
