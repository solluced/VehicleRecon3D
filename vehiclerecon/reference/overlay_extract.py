"""Color proposals, not semantic geometry or automatic reference acceptance."""
import numpy as np

def hsv(rgb):
    rgb=np.asarray(rgb,dtype=float)[...,:3]
    maximum=rgb.max(axis=-1);minimum=rgb.min(axis=-1);delta=maximum-minimum
    hue=np.zeros_like(maximum);nonzero=delta>1e-12
    for channel in range(3):
        mask=nonzero&(rgb[...,channel]==maximum)
        if channel==0:value=(rgb[...,1]-rgb[...,2])/np.maximum(delta,1e-12)%6
        elif channel==1:value=(rgb[...,2]-rgb[...,0])/np.maximum(delta,1e-12)+2
        else:value=(rgb[...,0]-rgb[...,1])/np.maximum(delta,1e-12)+4
        hue[mask]=value[mask]/6
    saturation=delta/np.maximum(maximum,1e-12)
    return hue,saturation,maximum

def components(mask,min_pixels=3):
    height,width=mask.shape;remaining=set(map(tuple,np.argwhere(mask)));result=[]
    while remaining:
        start=min(remaining);remaining.remove(start);stack=[start];points=[]
        while stack:
            y,x=stack.pop();points.append((x,y))
            for dy,dx in ((0,1),(1,0),(0,-1),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)):
                q=(y+dy,x+dx)
                if q in remaining:remaining.remove(q);stack.append(q)
        if len(points)<min_pixels:continue
        array=np.array(points);low=array.min(axis=0);high=array.max(axis=0)
        # A sparse deterministic boundary/curve proposal, deliberately unclassified.
        ordered=sorted(points,key=lambda p:(p[0],p[1]));step=max(1,len(ordered)//128)
        result.append({'pixels':len(points),'centroid_px':array.mean(axis=0).tolist(),
                       'bbox_px':[int(low[0]),int(low[1]),int(high[0])+1,int(high[1])+1],
                       'proposal_samples_px':[[int(x),int(y)] for x,y in ordered[::step][:128]]})
    return result

def extract(rgb):
    h,s,v=hsv(rgb);vivid=(s>.45)&(v>.45)
    masks={'orange':vivid&(h>.045)&(h<.14),'blue':vivid&(h>.51)&(h<.72),
           'red':vivid&((h<.04)|(h>.94)),'green':vivid&(h>.22)&(h<.46)}
    return {'schema_version':1,'status':'PROPOSAL_NOT_SEMANTIC_GEOMETRY',
            'convention':{'orange':'control points','blue':'visible splines','red':'inferred/hidden','green':'datum/axes'},
            'colors':{name:{'mask_pixels':int(mask.sum()),'components':components(mask)} for name,mask in masks.items()},
            'limitations':['Color segmentation has no semantic understanding.','Samples are raw pixel proposals, not validated cage curves.']}
