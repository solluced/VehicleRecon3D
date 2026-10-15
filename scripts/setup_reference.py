"""Calibrate bundled references in the supplied starter. Creates no vehicle geometry."""
import sys, hashlib, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project import *
import numpy as np
s=bpy.context.scene
verified=[]
for entry in json.loads((ROOT/'refs/manifest.json').read_text()):
    path=ROOT/entry['file']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'],path
    image=bpy.data.images.load(str(path),check_existing=True)
    assert tuple(image.size)==(entry['width'],entry['height']),path
    assert len(image.pixels)==entry['width']*entry['height']*4
    verified.append({'file':entry['file'],'pixels':list(image.size),'sha256':entry['sha256'],'decoded':True})
(ROOT/'validation/reference_inventory.json').write_text(json.dumps(verified,indent=2))
for obj in list(coll('00_REFERENCE').objects): bpy.data.objects.remove(obj,do_unlink=True)
camera('CAM_SIDE',(0,-10,H/2),(0,0,H/2),5.5)
camera('CAM_FRONT',(-10,0,H/2),(0,0,H/2),3.6)
camera('CAM_REAR',(10,0,H/2),(0,0,H/2),3.6)
camera('CAM_TOP',(0,0,10),(0,0,0),5.5)
camera('CAM_3Q',(-7.5,-7.5,4.6),(0,0,.75),5.8)
source=bpy.data.images.get('reference_multiview.png')
pixels=np.array(source.pixels[:],dtype=np.float32).reshape(1152,1536,4)[::-1,:,:]
for view,cfg in DATA['views'].items():
    l,t,r,b=cfg['crop']; ww=r-l; hh=b-t
    image=bpy.data.images.new('REF_CROP_'+view,ww,hh,alpha=True)
    image.pixels.foreach_set(pixels[t:b,l:r,:][::-1,:,:].flatten())
    image.filepath_raw=str(ROOT/f'refs/crop_{view}.png'); image.file_format='PNG'; image.save(); image.pack()
    if view=='side':
        verts=[(sx(l),1.35,sz(b)),(sx(r),1.35,sz(b)),(sx(r),1.35,sz(t)),(sx(l),1.35,sz(t))]
    elif view=='top':
        verts=[(tx(l),ty(b),-.08),(tx(r),ty(b),-.08),(tx(r),ty(t),-.08),(tx(l),ty(t),-.08)]
    else:
        center=cfg['centerline_u']; bw=cfg['body_bbox'][2]-cfg['body_bbox'][0]
        y=lambda u: (u-center)*W/bw*(-1 if view=='front' else 1)
        x=2.65 if view=='front' else -2.65
        verts=[(x,y(l),sz(b)),(x,y(r),sz(b)),(x,y(r),sz(t)),(x,y(l),sz(t))]
    m=bpy.data.materials.new('MAT_REFERENCE_'+view); m.use_nodes=True
    n=m.node_tree.nodes; n.clear(); tex=n.new('ShaderNodeTexImage'); tex.image=image
    emission=n.new('ShaderNodeEmission'); output=n.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(tex.outputs['Color'],emission.inputs['Color']); m.node_tree.links.new(emission.outputs[0],output.inputs[0])
    ob=mesh('REF_'+view.upper(),verts,[(0,1,2,3)],m,'00_REFERENCE')
    uv=ob.data.uv_layers.new()
    for loop,coord in zip(uv.data,[(0,0),(1,0),(1,1),(0,1)]): loop.uv=coord
    ob['source']=DATA['source']; ob['source_crop_px']=cfg['crop']; ob['calibration']='shared envelope, documented end-view rectification'
    ob.hide_render=True; ob.hide_set(True)
s['reference_calibration']='REGISTERED_WITH_DOCUMENTED_SOURCE_INCONSISTENCIES'
s['model_status']='REFERENCES_CALIBRATED_NO_BODY'
s['camera_status']='Orthographic cameras share one metric coordinate system'
notes=bpy.data.texts.get('READ_ME_FIRST'); notes.clear()
notes.write('Bundled references verified and packed. End views require documented horizontal rectification. Reference planes hidden for model renders. See docs/reference_dimensions.md.')
s.render.engine='CYCLES'; s.cycles.samples=1
s.view_settings.view_transform='Standard'
datum=emissive('MAT_DATUM',(0.02,.55,.8))
for view in ('side','top','front','rear'):
    temporary=[]
    ob=bpy.data.objects['REF_'+view.upper()]; ob.hide_render=False
    if view=='side':
        for u in (395,520,990,1128): temporary.append(curve('DATUM',[(sx(u),1.34,-.03),(sx(u),1.34,H+.03)],datum,.003,'00_REFERENCE',handles='VECTOR'))
        for z in (0,.406,H): temporary.append(curve('DATUM',[(sx(385),1.34,z),(sx(1140),1.34,z)],datum,.002,'00_REFERENCE',handles='VECTOR'))
        cam='CAM_SIDE'; dims=(1000,420)
    elif view=='top':
        temporary.append(curve('DATUM',[(-2.5,0,-.07),(2.5,0,-.07)],datum,.003,'00_REFERENCE',handles='VECTOR'))
        for u in (395,520,990,1128): temporary.append(curve('DATUM',[(sx(u),-1.05,-.07),(sx(u),1.05,-.07)],datum,.003,'00_REFERENCE',handles='VECTOR'))
        cam='CAM_TOP'; dims=(1000,460)
    else:
        x=2.64 if view=='front' else -2.64
        temporary.append(curve('DATUM',[(x,0,-.04),(x,0,H+.04)],datum,.003,'00_REFERENCE',handles='VECTOR'))
        for z in (0,.406,H): temporary.append(curve('DATUM',[(x,-1.05,z),(x,1.05,z)],datum,.002,'00_REFERENCE',handles='VECTOR'))
        cam='CAM_'+view.upper(); dims=(700,560)
    render('validation/alignment_'+view+'.png',cam,*dims)
    ob.hide_render=True
    for obj in temporary: bpy.data.objects.remove(obj,do_unlink=True)
canvas=np.ones((1120,2000,4),dtype=np.float32)
for view,x,y,ww,hh in [('side',0,0,1000,420),('top',1000,0,1000,460),('front',150,550,700,560),('rear',1150,550,700,560)]:
    im=bpy.data.images.load(str(ROOT/f'validation/alignment_{view}.png'),check_existing=True)
    a=np.array(im.pixels[:],dtype=np.float32).reshape(hh,ww,4)[::-1]
    canvas[y:y+hh,x:x+ww]=a
proof=bpy.data.images.new('REFERENCE_ALIGNMENT_PROOF',2000,1120)
proof.pixels.foreach_set(canvas[::-1].flatten()); proof.filepath_raw=str(ROOT/'validation/reference_alignment.png'); proof.file_format='PNG'; proof.save()
s.camera=bpy.data.objects['CAM_3Q']; save()
print('REFERENCE_SETUP_FINISHED: 5 images decoded, 4 packed calibrated planes, 4 camera alignment renders')

