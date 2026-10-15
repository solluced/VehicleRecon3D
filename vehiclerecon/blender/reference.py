"""Calibrated image geometry and proof renders, driven by project records."""
import bpy
import numpy as np
from ..reference.transforms import CalibrationTransform
from ..reference.panels import select_panel, inventory
from ..core.manifest import write_json
from .geometry import mesh, curve
from .materials import material
from .cameras import camera
from .scene import render, save

def build(project):
    config = project.generated('calibration',check=False)
    transform = CalibrationTransform(config)
    info = inventory(project)
    for entry in info.values():
        image = bpy.data.images.load(str(project.path(entry['path'])),check_existing=True)
        if list(image.size) != entry['size']:
            raise ValueError('Decoded image size mismatch')
        image.use_fake_user = True
        image.pack()
    for view,data in config['views'].items():
        path,separate = select_panel(project,view,data)
        source = bpy.data.images.load(str(path),check_existing=True)
        width,height = source.size
        pixels = np.array(source.pixels[:],dtype=np.float32).reshape(height,width,4)[::-1]
        l,t,r,b = data['crop']
        crop = pixels if separate else pixels[t:b,l:r]
        hh,ww = crop.shape[:2]
        image = bpy.data.images.new('REF_CROP_'+view,ww,hh,alpha=True)
        image.pixels.foreach_set(crop[::-1].flatten())
        image.filepath_raw = str(project.path(f'generated/crop_{view}.png'))
        image.file_format = 'PNG'
        image.save()
        image.pack()
        mat = bpy.data.materials.new('MAT_REFERENCE_'+view)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        tex = nodes.new('ShaderNodeTexImage');tex.image=image
        emission = nodes.new('ShaderNodeEmission');out = nodes.new('ShaderNodeOutputMaterial')
        mat.node_tree.links.new(tex.outputs['Color'],emission.inputs['Color'])
        mat.node_tree.links.new(emission.outputs[0],out.inputs[0])
        vertices = [[a+d for a,d in zip(transform.pixel_to_world(view,u,v),data['plane_offset'])]
                    for u,v in [(l,b),(r,b),(r,t),(l,t)]]
        obj = mesh('REF_'+view.upper(),vertices,[(0,1,2,3)],mat,'00_REFERENCE')
        uv = obj.data.uv_layers.new()
        for loop,point in zip(uv.data,[(0,0),(1,0),(1,1),(0,1)]):
            loop.uv=point
        obj['source']=str(path)
        obj['source_crop_px']=data['crop']
        obj.hide_render=True
        obj.hide_set(True)
        camera(data['camera'],'09_PRESENTATION')
    camera(config['perspective_camera'],'09_PRESENTATION')
    write_json(project.path('validation/reference_inventory.json'),info)
    proof(project,config)
    bpy.context.scene.camera = bpy.data.objects[config['perspective_camera']['name']]
    save(project.path('.cache/calibration.blend'))

def proof(project,config):
    scene=bpy.context.scene
    scene.cycles.samples=1
    scene.view_settings.view_transform='Standard'
    style=config['datums']['style']
    material(style)
    for view,data in config['views'].items():
        obj=bpy.data.objects['REF_'+view.upper()]
        obj.hide_render=False
        temporary=[]
        for line in config['datums']['views'][view]:
            temporary.append(curve('DATUM',line['points'],style['name'],line['radius'],'00_REFERENCE',handles='VECTOR'))
        render(project.path(f'validation/alignment_{view}.png'),data['camera']['name'],*data['camera']['size'])
        obj.hide_render=True
        for datum in temporary:bpy.data.objects.remove(datum,do_unlink=True)
    layout=config['proof_layout']
    width,height=layout['size']
    canvas=np.ones((height,width,4),dtype=np.float32)
    for entry in layout['panels']:
        image=bpy.data.images.load(str(project.path('validation/alignment_'+entry['view']+'.png')),check_existing=True)
        ww,hh=image.size;x,y=entry['position']
        canvas[y:y+hh,x:x+ww]=np.array(image.pixels[:],dtype=np.float32).reshape(hh,ww,4)[::-1]
    image=bpy.data.images.new('REFERENCE_ALIGNMENT_PROOF',width,height)
    image.pixels.foreach_set(canvas[::-1].flatten())
    image.filepath_raw=str(project.path('validation/reference_alignment.png'));image.file_format='PNG';image.save()
