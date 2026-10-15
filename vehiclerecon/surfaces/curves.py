"""Pure boundary mathematics; Blender can inject its float32 vector backend."""
import math
from ..core.errors import SchemaError

class Vector(tuple):
    def __new__(cls, values): return super().__new__(cls,map(float,values))
    def __add__(self, other): return type(self)(a+b for a,b in zip(self,other))
    def __sub__(self, other): return type(self)(a-b for a,b in zip(self,other))
    def __mul__(self, scalar): return type(self)(a*scalar for a in self)
    __rmul__ = __mul__
    def __truediv__(self, scalar): return self*(1/scalar)
    def copy(self): return type(self)(self)
    def lerp(self, other, t): return self*(1-t)+other*t
    def dot(self, other): return sum(a*b for a,b in zip(self,other))
    @property
    def length(self): return math.sqrt(self.dot(self))
    x=property(lambda s:s[0]); y=property(lambda s:s[1]); z=property(lambda s:s[2])

def cubic(a,b,c,d,t):
    return a*(1-t)**3+3*b*t*(1-t)**2+3*c*t*t*(1-t)+d*t**3

def polyline(points,vector=Vector):
    points=list(map(vector,points))
    if len(points)<2:raise SchemaError('Polyline needs two points')
    def sample(t):
        value=max(0,min(1,t))*(len(points)-1)
        i=min(len(points)-2,int(value))
        return points[i].lerp(points[i+1],value-i)
    return sample

def chord_hermite(points,vector=Vector):
    points=list(map(vector,points))
    if len(points)<2:raise SchemaError('Hermite curve needs two points')
    distances=[0.]
    for a,b in zip(points,points[1:]):
        distance=(b-a).length
        if distance<=1e-12:raise SchemaError('Repeated Hermite controls')
        distances.append(distances[-1]+distance)
    distances=[v/distances[-1] for v in distances]
    slopes=[]
    for i in range(len(points)):
        a=max(0,i-1);b=min(len(points)-1,i+1)
        slopes.append((points[b]-points[a])/(distances[b]-distances[a]))
    def sample(t):
        if t<=0:return points[0].copy()
        if t>=1:return points[-1].copy()
        i=next(i for i in range(len(points)-1) if distances[i]<=t<=distances[i+1])
        h=distances[i+1]-distances[i];u=(t-distances[i])/h
        return (2*u**3-3*u*u+1)*points[i]+(u**3-2*u*u+u)*h*slopes[i]+(-2*u**3+3*u*u)*points[i+1]+(u**3-u*u)*h*slopes[i+1]
    return sample

def shape_preserving_hermite(points,vector=Vector,endpoint_epsilon=0):
    points=list(map(vector,points));derivatives=[]
    if len(points)<2:raise SchemaError('Hermite curve needs two points')
    for i,point in enumerate(points):
        if i==0:tangent=points[1]-points[0]
        elif i==len(points)-1:tangent=points[-1]-points[-2]
        else:
            before=points[i]-points[i-1];after=points[i+1]-points[i]
            tangent=vector(tuple(2*a*b/(a+b) if a*b>0 else 0 for a,b in zip(before,after)))
        derivatives.append(tangent)
    def sample(t):
        f=min(len(points)-1-endpoint_epsilon,max(0,t*(len(points)-1)))
        i=min(len(points)-2,int(f));z=f-i
        return (2*z**3-3*z*z+1)*points[i]+(z**3-2*z*z+z)*derivatives[i]+(-2*z**3+3*z*z)*points[i+1]+(z**3-z*z)*derivatives[i+1]
    return sample

def at_x(points,x,iterations=30):
    if len(points)<2 or any(a['co'][0]>=b['co'][0] for a,b in zip(points,points[1:])):
        raise SchemaError('Bezier X controls must be strictly increasing')
    if x<=points[0]['co'].x:return points[0]['co'].copy()
    if x>=points[-1]['co'].x:return points[-1]['co'].copy()
    for a,b in zip(points,points[1:]):
        if a['co'].x<=x<=b['co'].x:
            lo=0.;hi=1.
            for _ in range(iterations):
                t=(lo+hi)/2;q=cubic(a['co'],a['right'],b['left'],b['co'],t)
                if q.x<x:lo=t
                else:hi=t
            return q

def bezier_rail_range(points,x_start,x_end):
    return lambda t:at_x(points,x_start+(x_end-x_start)*t)
