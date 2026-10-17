"""Pixel-space proposal fitting. No CV runtime, canonical mutation or world solve.

Each output segment retains the original sample interval. Distance to a convex
segment is convex, so the largest original-vertex/chord distance bounds the
whole source interval. A Bezier lies in its control hull. The sum of those two
capsule radii is a continuous, bidirectional Hausdorff upper bound, since both
paths join the chord endpoints. Point-count limits never override this bound.
"""
import math
import numpy as np


def points(value):
    p=np.asarray(value,dtype=float)
    if p.ndim!=2 or p.shape[1]!=2 or not 2<=len(p)<=32768 or not np.isfinite(p).all():
        raise ValueError('A contour needs 2..32768 finite source pixel pairs')
    return p


def segment_dist(p,a,b):
    v=b-a;d=float(v@v)
    t=np.clip((p-a)@v/d,0,1) if d>1e-20 else np.zeros(len(p))
    return np.linalg.norm(p-a-t[:,None]*v,axis=1)


def _indices(p,tolerance,preserve):
    keep={0,len(p)-1}
    if preserve:
        for i in range(1,len(p)-1):
            a=p[i]-p[max(0,i-4)];b=p[min(len(p)-1,i+4)]-p[i]
            length=np.linalg.norm(a)*np.linalg.norm(b)
            if length>1e-9 and float(a@b)/length<.5:keep.add(i)
    if len(keep)>1024:raise ValueError('Important corners exceed the bounded 1024-point proposal budget')
    stack=list(zip(sorted(keep)[:-1],sorted(keep)[1:]))
    while stack:
        a,b=stack.pop()
        if b-a<2:continue
        d=segment_dist(p[a+1:b],p[a],p[b]);i=int(np.argmax(d))
        if d[i]>tolerance:
            m=a+1+i;keep.add(m);stack.extend(((a,m),(m,b)))
            if len(keep)>1024:raise ValueError('Deviation requires more than 1024 points; trim the contour or raise tolerance')
    return sorted(keep)


def _flatten(a,b,c,d,tolerance=.025,depth=0):
    if depth>=14 or max(segment_dist(np.array([b,c]),a,d))<=tolerance:
        return [a,d]
    ab=(a+b)/2;bc=(b+c)/2;cd=(c+d)/2;abc=(ab+bc)/2;bcd=(bc+cd)/2;mid=(abc+bcd)/2
    return _flatten(a,ab,abc,mid,tolerance,depth+1)[:-1]+_flatten(mid,bcd,cd,d,tolerance,depth+1)


def fit_contour(value,*,tolerance=2.,max_points=512,preserve_corners=True,spline=False,closed=False):
    p=points(value)
    if len(np.unique(p,axis=0))<2:raise ValueError('A contour needs distinct source points')
    if not math.isfinite(tolerance) or not .05<=tolerance<=32 or not 2<=max_points<=1024:
        raise ValueError('Tolerance must be .05..32 px and maximum points 2..1024')
    if closed and not np.array_equal(p[0],p[-1]):p=np.vstack((p,p[0]))
    # A closed path is split at its farthest datum before RDP; no degenerate
    # endpoint chord can erase the contour or its original start identity.
    if closed:
        mid=int(np.argmax(np.linalg.norm(p-p[0],axis=1)))
        left=_indices(p[:mid+1],tolerance*.45,preserve_corners)
        right=[mid+i for i in _indices(p[mid:],tolerance*.45,preserve_corners)]
        indices=left+right[1:]
    else:indices=_indices(p,tolerance*.45,preserve_corners)
    if len(indices)>max_points:raise ValueError('Point budget cannot meet deviation/corner bounds; raise the budget or tolerance, or trim the contour')
    q=p[indices];tangents=np.zeros_like(q)
    for i in range(1,len(q)-1):
        a=q[i]-q[i-1];b=q[i+1]-q[i]
        norm=np.linalg.norm(a)*np.linalg.norm(b)
        if not preserve_corners or norm>1e-9 and float(a@b)/norm>.5:
            tangents[i]=(q[i+1]-q[i-1])/6
    if len(q)>1:
        tangents[0]=(q[1]-q[0])/3;tangents[-1]=(q[-1]-q[-2])/3
    errors=[float(max(segment_dist(p[a:b+1],p[a],p[b]))) for a,b in zip(indices,indices[1:])]
    factor=1. if spline else 0.
    for _ in range(18):
        left=q-tangents*factor;right=q+tangents*factor;bounds=[]
        for i,(a,b) in enumerate(zip(q,q[1:])):
            hull=max(segment_dist(np.array([right[i],left[i+1]]),a,b)) if spline else 0
            bounds.append(errors[i]+float(hull))
        if max(bounds,default=0)<=tolerance:break
        factor*=.5
    else:raise ValueError('Cannot certify spline deviation within the requested tolerance')
    samples=[];distances=[]
    for i,(a,b) in enumerate(zip(indices,indices[1:])):
        flat=np.array(_flatten(q[i],right[i],left[i+1],q[i+1])) if spline else q[i:i+2]
        samples.extend(flat[:-1].tolist())
        dist=np.full(b-a+1,float('inf'))
        for u,v in zip(flat,flat[1:]):dist=np.minimum(dist,segment_dist(p[a:b+1],u,v))
        distances.extend(dist.tolist())
    samples.append(q[-1].tolist())
    knots=[{'pixel':v.tolist(),'left':left[i].tolist(),'right':right[i].tolist()} for i,v in enumerate(q)] if spline else None
    return {'kind':'spline' if spline else 'polyline','points':q.tolist(),'knots':knots,'closed':bool(closed),
            'preview_points':samples,'original_points':p.tolist(),'fit':{
                'max_deviation_px':max(distances,default=0),'rms_deviation_px':float(np.sqrt(np.mean(np.square(distances)))),
                'certified_max_deviation_px':max(bounds,default=0),'measurement_flatten_error_px':.025 if spline else 0,
                'tolerance_px':tolerance,'control_point_count':len(q),'original_sample_count':len(p),
                'preserve_corners':bool(preserve_corners),'method':'RDP intervals + bounded cubic control hull' if spline else 'RDP intervals / continuous chord bound'}}
