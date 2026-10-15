from .curves import Vector,cubic,polyline,shape_preserving_hermite

def cubic_boundary_roll(inner,outer,first_control_scale,second_scale,slopes,vector=Vector):
    def sample(a,r):
        f=inner(a);h=outer(a);delta=h-f
        c1=f+vector(tuple(value*scale for value,scale in zip(delta,first_control_scale)))
        if len(slopes)==1:slope=slopes[0]
        else:
            k=min(len(slopes)-2,int(a*(len(slopes)-1)));z=min(1,a*(len(slopes)-1)-k)
            slope=slopes[k]*(1-z)+slopes[k+1]*z
        c2=h+vector((0,(f.y-h.y)*second_scale,-max(0,f.y-h.y)*second_scale*slope))
        return cubic(f,c1,c2,h,r)
    return sample

def ribbon(curve,start,end,vector=Vector):
    start,end=vector(start),vector(end)
    return lambda u,v:curve(u)+start.lerp(end,v)

def arch_annulus(inner_points,outer_points,first_control_scale,second_scale,slopes,vector=Vector):
    return cubic_boundary_roll(shape_preserving_hermite(inner_points,vector),shape_preserving_hermite(outer_points,vector),first_control_scale,second_scale,slopes,vector)

def grid(sample,us,vs):
    vertices=[sample(u,v) for v in vs for u in us]
    faces=[]
    for j in range(len(vs)-1):
        for i in range(len(us)-1):
            a=j*len(us)+i;faces.append((a,a+1,a+1+len(us),a+len(us)))
    return vertices,faces

def parameters(n,support):
    return [0,support[0]]+[i/n for i in range(1,n)]+[support[1],1]

def boundary_stitch(bottom,top,rows):
    if len(bottom)!=len(top) or len(bottom)<2:
        from ..core.errors import SchemaError
        raise SchemaError('Stitch boundaries require matching cardinality')
    return grid(lambda u,v:bottom[int(u)].lerp(top[int(u)],v),range(len(bottom)),[0]+list(rows))
