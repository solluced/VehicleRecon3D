"""Reusable annular profiles and radial spokes; no car-specific sizes."""
import math
from ..core.errors import SchemaError

def revolved(profile,segments):
    if segments<3 or len(profile)<3:raise SchemaError('Invalid revolved wheel profile')
    vertices=[];faces=[]
    for radius,y in profile:
        for i in range(segments):
            a=i*math.tau/segments;vertices.append((radius*math.cos(a),y,radius*math.sin(a)))
    for j in range(len(profile)):
        for i in range(segments):faces.append((j*segments+i,j*segments+(i+1)%segments,((j+1)%len(profile))*segments+(i+1)%segments,((j+1)%len(profile))*segments+i))
    return vertices,faces

def radial_spokes(polygon,count,depth,side):
    if count<1:raise SchemaError('Spoke count must be positive')
    return [[(r*math.cos(i*math.tau/count+a),side*depth,r*math.sin(i*math.tau/count+a)) for r,a in polygon] for i in range(count)]
