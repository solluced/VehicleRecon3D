"""Deterministic CPU annotation proposals. Coordinates are original pixels."""
import heapq
import math
import numpy as np
from vehiclerecon.authoring.contours import fit_contour

PRESETS={'Weak':(24,64),'Normal':(55,140),'Strong':(100,220)}

def _raster(cv,binary,color):
    rgba=np.zeros((*binary.shape,4),np.uint8);rgba[:,:,:3]=color;rgba[:,:,3]=np.where(binary>0,180,0)
    return cv.imencode('.png',rgba)[1].tobytes()

def _field(cv,image,box,p,ctx):
    key=('edges',ctx['source_hash'],tuple(box),p.get('preset','Normal'),p.get('threshold'),p.get('minimum_contrast',0))
    found=ctx['cache'].get(key)
    if found is not None:return found
    x,y,r,b=box;gray=cv.cvtColor(image[y:b,x:r],cv.COLOR_BGR2GRAY)
    gray=cv.GaussianBlur(gray,(3,3),.8)
    low,high=PRESETS[p.get('preset','Normal')]
    if 'threshold' in p:high=p['threshold'];low=high*.4
    edge=cv.Canny(gray,low,high,L2gradient=True)
    gx=cv.Sobel(gray,cv.CV_32F,1,0);gy=cv.Sobel(gray,cv.CV_32F,0,1)
    strength=np.minimum(cv.magnitude(gx,gy)/400,1)
    strength[strength*255<p.get('minimum_contrast',0)]=0
    value={'edge':edge,'strength':strength};ctx['cache'].put(key,value)
    return value

def _component(p,ident,closed=True,tolerance=2):
    fit=fit_contour(p,tolerance=tolerance,max_points=1024,preserve_corners=False,closed=closed)
    return {'id':ident,'semantic_role':'UNKNOWN','status':'ACTIVE','score':None,**fit}

def _contours(cv,mask,offset,p,ctx):
    contours,_=cv.findContours(mask,cv.RETR_EXTERNAL if p.get('outer_only') else cv.RETR_LIST,cv.CHAIN_APPROX_NONE)
    contours=sorted(contours,key=lambda c:(-cv.arcLength(c,True),cv.boundingRect(c)))
    result=[];total=0
    for c in contours:
        ctx['check']()
        if len(c)<8 or len(c)>32760 or total+len(c)>65536:continue
        pts=c[:,0,:].astype(float)+np.array(offset)
        try:component=_component(pts,'component_'+str(len(result)),True,p.get('tolerance',2))
        except ValueError:continue
        result.append(component);total+=len(c)
        if len(result)>=16:break
    return result

def _smart(cv,image,box,p,ctx):
    trail=np.array(p.get('trajectory',[]),float)
    if len(trail)<2:raise ValueError('Smart Edge needs a start and a directed pointer trajectory')
    if not np.isfinite(trail).all():raise ValueError('Finite source pixels required')
    radius=p.get('search_radius',24)
    lower=np.maximum(np.floor((trail.min(axis=0)-radius)/32)*32,box[:2]).astype(int)
    upper=np.minimum(np.ceil((trail.max(axis=0)+radius+1)/32)*32,box[2:]).astype(int)
    x,y=lower;r,b=upper;w,h=r-x,b-y
    if w<3 or h<3 or w*h>262144:raise ValueError('Smart Edge search is local; click a segment before spanning more than 262144 ROI pixels')
    field=_field(cv,image,[x,y,r,b],p,ctx);edge=field['edge'];strength=field['strength']
    if not edge.any() or strength.max()<p.get('minimum_contrast',0)/255:
        return {'components':[],'warnings':['No usable contrast in the local search ROI']}
    path_mask=np.ones((h,w),np.uint8)*255
    local=np.rint(trail-lower).astype(int);local[:,0]=np.clip(local[:,0],0,w-1);local[:,1]=np.clip(local[:,1],0,h-1)
    cv.polylines(path_mask,[local],False,0,1)
    proximity=cv.distanceTransform(path_mask,cv.DIST_L2,3)
    attraction=p.get('edge_attraction',5.)
    cost=(1+attraction*(1-np.maximum(strength,edge/255))+.08*proximity).astype(np.float32)
    def snapped(point):
        sx,sy=point;ys,xs=np.nonzero(edge)
        d=np.hypot(xs-sx,ys-sy);valid=d<=radius
        if not valid.any():return int(sx),int(sy)
        score=np.where(valid,d+.5*radius*(1-strength[ys,xs]),np.inf);i=int(np.argmin(score))
        return int(xs[i]),int(ys[i])
    start=snapped(local[0]);end=snapped(local[-1])
    if start==end:return {'components':[],'warnings':['Move farther from the start to define a feature segment']}
    direction=np.array(end)-start;direction=direction/max(np.linalg.norm(direction),1)
    distances=np.full((h,w),np.inf);distances[start[1],start[0]]=0;parents={};queue=[(0.,0.,start)];visited=0
    steps=[(dx,dy,math.hypot(dx,dy)) for dy in (-1,0,1) for dx in (-1,0,1) if dx or dy]
    while queue:
        _,distance,at=heapq.heappop(queue)
        if distance!=distances[at[1],at[0]]:continue
        if at==end:break
        visited+=1
        if visited%256==0:ctx['check']()
        if visited>80000:raise ValueError('Local path search budget exhausted; commit a shorter segment')
        for dx,dy,length in steps:
            nx,ny=at[0]+dx,at[1]+dy
            if not 0<=nx<w or not 0<=ny<h:continue
            turn=p.get('smoothness',.3)*(1-float(np.dot(direction,[dx/length,dy/length])))
            candidate=distance+length*(float(cost[ny,nx])+turn)
            if candidate<distances[ny,nx]:
                distances[ny,nx]=candidate;parents[(nx,ny)]=at
                heuristic=math.hypot(end[0]-nx,end[1]-ny)
                heapq.heappush(queue,(candidate+heuristic,candidate,(nx,ny)))
    if end not in parents:return {'components':[],'warnings':['No bounded path found']}
    path=[end]
    while path[-1]!=start:path.append(parents[path[-1]])
    path.reverse();world=(np.array(path)+lower).tolist()
    return {'components':[_component(world,'component_0',False,p.get('tolerance',1))],
            'search_pixels':int(w*h),'expanded_nodes':visited,'warnings':['User-directed local contrast path; semantics UNKNOWN']}

def run(capability,raw,p,ctx):
    import cv2 as cv
    cv.setNumThreads(1);cv.setRNGSeed(0);cv.ocl.setUseOpenCL(False);ctx['check']()
    key=('image',ctx['source_hash']);image=ctx['cache'].get(key)
    if image is None:
        image=cv.imdecode(np.frombuffer(raw,np.uint8),cv.IMREAD_COLOR|cv.IMREAD_IGNORE_ORIENTATION)
        if image is None or image.shape[0]*image.shape[1]>16777216:raise ValueError('CV source decode budget exceeded')
        ctx['cache'].put(key,image)
    height,width=image.shape[:2];crop=ctx['crop'];box=p.get('roi',crop)
    x,y,r,b=map(int,box)
    if not (crop[0]<=x<r<=crop[2]<=width and crop[1]<=y<b<=crop[3]<=height):
        raise ValueError('ROI must stay inside the selected source-view crop')
    if capability=='smart_edge':return _smart(cv,image,[x,y,r,b],p,ctx)
    field=_field(cv,image,[x,y,r,b],p,ctx) if capability!='segment_object' else None
    ctx['check']()
    if capability=='detect_edges':
        return {'components':[],'rasters':{'edges':_raster(cv,field['edge'],[255,195,90])},'raster_bounds':[x,y,r,b],
                'warnings':['Binary Canny diagnostic, not a semantic probability map']}
    if capability=='trace_contour':return {'components':_contours(cv,field['edge'],[x,y],p,ctx),'warnings':['Connected edges may include reflections/background; choose components explicitly']}
    if (r-x)*(b-y)>4194304:raise ValueError('Segmentation/wheel ROI exceeds 4194304 pixels; narrow the source ROI')
    if capability=='segment_object':
        roi=image[y:b,x:r].copy();h,w=roi.shape[:2]
        if min(h,w)<8:raise ValueError('Mask ROI needs at least 8 pixels per side')
        mask=np.full((h,w),cv.GC_PR_BGD,np.uint8);mask[2:-2,2:-2]=cv.GC_PR_FGD
        mask[:2]=mask[-2:]=cv.GC_BGD;mask[:,:2]=mask[:,-2:]=cv.GC_BGD
        for stroke in p.get('strokes',[]):
            ctx['check']();label=cv.GC_FGD if stroke['label']=='foreground' else cv.GC_BGD
            pts=np.rint(np.array(stroke['points'])-[x,y]).astype(np.int32)
            radius=stroke.get('radius',8)
            if len(pts)>1:cv.polylines(mask,[pts],False,int(label),2*radius)
            for point in pts:cv.circle(mask,tuple(point),radius,int(label),-1)
        # Keep a guaranteed exterior; painting cannot turn the entire ROI into FG.
        mask[0]=mask[-1]=cv.GC_BGD;mask[:,0]=mask[:,-1]=cv.GC_BGD
        bg=np.zeros((1,65),np.float64);fg=np.zeros((1,65),np.float64)
        for iteration in range(2):
            ctx['check']();cv.grabCut(roi,mask,None,bg,fg,1,cv.GC_INIT_WITH_MASK if iteration==0 else cv.GC_EVAL)
        binary=np.where((mask==cv.GC_FGD)|(mask==cv.GC_PR_FGD),255,0).astype(np.uint8)
        ctx['check']();components=_contours(cv,binary,[x,y],{**p,'outer_only':True},ctx)
        return {'components':components,'rasters':{'mask':_raster(cv,binary,[225,140,185])},'raster_bounds':[x,y,r,b],
                'mask':{'encoding':'RGBA8-alpha','foreground_alpha':180,'background_alpha':0,'bounds':[x,y,r,b],
                        'foreground_pixels':int(np.count_nonzero(binary))},
                'warnings':['Classical GrabCut color/contrast region; no semantic vehicle recognition']}
    if capability=='detect_wheels':
        contours,_=cv.findContours(field['edge'],cv.RETR_LIST,cv.CHAIN_APPROX_NONE);found=[]
        for c in contours:
            ctx['check']()
            if len(c)<12:continue
            (cx,cy),radius=cv.minEnclosingCircle(c);perimeter=cv.arcLength(c,True);area=abs(cv.contourArea(c))
            score=4*math.pi*area/max(perimeter*perimeter,1)
            if not p.get('min_radius',8)<=radius<=p.get('max_radius',min(r-x,b-y)/2) or score<.68:continue
            found.append((float(cx+x),float(cy+y),float(radius),min(1,float(score))))
        accepted=[]
        for cx,cy,radius,score in sorted(found,key=lambda c:(-c[3],c[0],c[1],c[2])):
            if any(math.hypot(cx-a[0],cy-a[1])<max(3,.2*radius) and abs(radius-a[2])<.25*radius for a in accepted):continue
            accepted.append((cx,cy,radius,score))
            if len(accepted)>=16:break
        accepted.sort()
        return {'components':[{'id':f'component_{i}','kind':'circle','center':[a,b],'radius_px':radius,
                'semantic_role':'UNKNOWN','status':'ACTIVE','score':score,'score_meaning':'Geometric circularity, not probability of a wheel'}
                for i,(a,b,radius,score) in enumerate(accepted)],'warnings':['Circle candidates can be wheels, logos or background; no automatic choice']}
    raise ValueError('Unsupported registered capability')
