"""Render real geometry masks; compare fixed-camera projection to source traces.

Run inside Blender with the saved project. No independent per-view fitting,
bounding-box rescaling, synthetic model masks, or acceptance overrides.
"""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project import *
import numpy as np
from bpy_extras.object_utils import world_to_camera_view

traces=json.loads((ROOT/'refs/silhouette_traces.json').read_text())
s=bpy.context.scene
out=ROOT/'validation/masks'; out.mkdir(exist_ok=True)
saved={ob.name:ob.hide_render for ob in bpy.data.objects}
for col in ('00_REFERENCE','01_CURVE_CAGE','09_PRESENTATION'):
    for ob in coll(col).objects:
        if ob.type!='CAMERA': ob.hide_render=True
for ob in bpy.data.objects:
    if ob.name.startswith('WIRE_'):ob.hide_render=True
s.render.engine='CYCLES'; s.cycles.samples=1; s.render.film_transparent=False
s.view_settings.view_transform='Standard'
oldworld=s.world
white=bpy.data.worlds.new('MASK_WORLD'); white.use_nodes=True
white.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1)
s.world=white
black=emissive('MAT_SILHOUETTE_BLACK',(0,0,0)); s.view_layers[0].material_override=black

def polygon_mask(points,w,h):
    yy,xx=np.mgrid[0:h,0:w]; xx=xx+.5; yy=yy+.5; inside=np.zeros((h,w),dtype=bool)
    for (ax,ay),(bx,by) in zip(points,points[1:]+points[:1]):
        if abs(by-ay)<1e-10:continue
        inside^=((ay>yy)!=(by>yy))&(xx<(bx-ax)*(yy-ay)/(by-ay)+ax)
    return inside
def image_save(name,array):
    hh,ww=array.shape[:2]
    im=bpy.data.images.new(name,ww,hh,alpha=True)
    im.pixels.foreach_set(np.asarray(array[::-1],dtype=np.float32).flatten())
    im.filepath_raw=str(out/(name+'.png')); im.file_format='PNG'; im.save()
def bbox(mask):
    yy,xx=np.where(mask)
    return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)] if len(xx) else None

results={}
for view,w,h,threshold in [('side',1200,560,.94),('top',1200,600,.92),('front',800,640,.92),('rear',800,640,.90)]:
    cam=bpy.data.objects['CAM_'+view.upper()]; s.camera=cam
    s.render.resolution_x=w; s.render.resolution_y=h; s.render.resolution_percentage=100
    cfg=DATA['views'][view]
    def world(u,v):
        if view=='side':return (sx(u),0,sz(v))
        if view=='top':return (tx(u),ty(v),0)
        bw=cfg['body_bbox'][2]-cfg['body_bbox'][0]
        return (0,(u-cfg['centerline_u'])*W/bw*(-1 if view=='front' else 1),sz(v))
    def project(u,v):
        q=world_to_camera_view(s,cam,Vector(world(u,v)))
        return (q.x*w,(1-q.y)*h)
    reference=polygon_mask([project(*a) for a in traces[view]['body']],w,h)
    for component in traces[view].get('components',[]):
        reference|=polygon_mask([project(*a) for a in component],w,h)
    for u,v,r in traces[view].get('tires',[]):
        points=[project(u+r*math.cos(a),v+r*math.sin(a)) for a in [i*math.tau/128 for i in range(128)]]
        reference|=polygon_mask(points,w,h)
    render('validation/masks/model_'+view+'.png',cam.name,w,h)
    im=bpy.data.images.load(str(out/('model_'+view+'.png')),check_existing=True)
    rgba=np.array(im.pixels[:]).reshape(h,w,4)[::-1]
    model=rgba[:,:,:3].mean(axis=2)<.5
    intersection=np.count_nonzero(model&reference); union=np.count_nonzero(model|reference)
    iou=intersection/union if union else 0
    mismatch=np.count_nonzero(model^reference)
    rb=bbox(reference); mb=bbox(model)
    results[view]={'status':'PASS' if iou>=threshold else 'FAIL','iou':round(iou,6),'threshold':threshold,
        'pixel_mismatch_percent_of_frame':round(100*mismatch/(w*h),4),
        'pixel_mismatch_percent_of_union':round(100*mismatch/max(1,union),4),
        'reference_bbox_px':rb,'model_bbox_px':mb,
        'bbox_difference_px': [b-a for a,b in zip(rb,mb)] if rb and mb else None,
        'render_size':[w,h]}
    mask_rgba=np.ones((h,w,4)); mask_rgba[reference,:3]=0
    image_save('reference_'+view,mask_rgba)
    comparison=np.ones((h,w,4))
    comparison[reference&model,:3]=(.55,.65,.68)
    comparison[reference&~model,:3]=(1,.12,.12)
    comparison[model&~reference,:3]=(.05,.25,1)
    image_save('comparison_'+view,comparison)
passed=all(v['status']=='PASS' for v in results.values())
report={'status':'silhouette_pass_surface_review_pending' if passed else 'silhouette_fail_refinement_required',
    'source_blend_sha256':hashlib.sha256((ROOT/'tesla_surface_model.blend').read_bytes()).hexdigest(),
    'reference_calibration':'REGISTERED_WITH_DOCUMENTED_SOURCE_INCONSISTENCIES',
    'source_mask_method':traces['method'],'model_mask_method':'Actual opaque black-material Blender renders from fixed calibrated cameras; no per-view rescaling',
    'cage_status':s.get('cage_status'),'model_status':s.get('model_status'),
    'dimensions':DATA['scale'],'views':results,'silhouette_pass':passed,
    'surface_quality_pass':False,'export_allowed':False,'complete':False}
(ROOT/'validation/report.json').write_text(json.dumps(report,indent=2))
s.world=oldworld; s.view_layers[0].material_override=None
for name,value in saved.items():
    if name in bpy.data.objects:bpy.data.objects[name].hide_render=value
print(json.dumps(results,indent=2))
print('SILHOUETTE_GATE',passed,'SURFACE_GATE',False)
