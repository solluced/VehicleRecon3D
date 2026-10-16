import bpy,math
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
from ..reference.transforms import CalibrationTransform
from ..validation.silhouette import polygon_mask,metrics,require
from ..core.manifest import digest_file,write_json
from ..validation.report import model_inputs_hash
from .scene import render
from .materials import material

def image_save(path,array):
    height,width=array.shape[:2]
    image=bpy.data.images.new(path.stem,width,height,alpha=True)
    image.pixels.foreach_set(np.asarray(array[::-1],dtype=np.float32).flatten())
    image.filepath_raw=str(path);image.file_format='PNG';image.save()

def validate(project,label='surface'):
    traces=project.generated('silhouette_traces',check=False)
    calibration=project.generated('calibration',check=False)
    transform=CalibrationTransform(calibration)
    scene=bpy.context.scene
    saved={o.name:o.hide_render for o in bpy.data.objects}
    for collection in project.data['export']['excluded_collections']:
        for obj in bpy.data.collections[collection].objects:
            if obj.type!='CAMERA':obj.hide_render=True
    for obj in bpy.data.objects:
        if obj.get('source_topology_object'):obj.hide_render=True
    scene.render.engine='CYCLES';scene.cycles.samples=1
    scene.render.film_transparent=False;scene.view_settings.view_transform='Standard'
    oldworld=scene.world
    white=bpy.data.worlds.new('MASK_WORLD');white.use_nodes=True
    white.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1)
    scene.world=white
    black=material({'name':'MASK_BLACK','kind':'emission','color':[0,0,0]})
    scene.view_layers[0].material_override=black
    out=project.path(f'validation/{label}_masks');out.mkdir(exist_ok=True)
    results={}
    try:
        for config in project.data['presentation']['views']:
            view=config['view']
            if view not in calibration['views']:continue
            width,height=config['size'];camera=bpy.data.objects[config['camera']]
            scene.camera=camera;scene.render.resolution_x=width;scene.render.resolution_y=height
            scene.render.resolution_percentage=100
            def project_pixel(u,v):
                q=world_to_camera_view(scene,camera,Vector(transform.pixel_to_world(view,u,v)))
                return (q.x*width,(1-q.y)*height)
            def projected_boundary(points):
                if view not in transform.rectifications:
                    return [project_pixel(*p) for p in points]
                result=[]
                for point in transform.pixel_polyline_to_world(view,points,closed=True):
                    q=world_to_camera_view(scene,camera,Vector(point))
                    result.append((q.x*width,(1-q.y)*height))
                return result
            reference=polygon_mask(projected_boundary(traces[view]['body']),width,height)
            for component in traces[view].get('components',[]):
                reference|=polygon_mask(projected_boundary(component),width,height)
            for u,v,radius in traces[view].get('tires',[]):
                points=[(u+radius*math.cos(a),v+radius*math.sin(a)) for a in [i*math.tau/128 for i in range(128)]]
                reference|=polygon_mask(projected_boundary(points),width,height)
            path=out/f'model_{view}.png'
            render(path,camera.name,width,height)
            image=bpy.data.images.load(str(path),check_existing=True)
            rgba=np.array(image.pixels[:]).reshape(height,width,4)[::-1]
            model=rgba[:,:,:3].mean(axis=2)<.5
            result=metrics(reference,model,project.data['validation']['thresholds'][view])
            results[view]=result
            reference_image=np.ones((height,width,4));reference_image[reference,:3]=0
            image_save(out/f'reference_{view}.png',reference_image)
            comparison=np.ones((height,width,4));comparison[reference&model,:3]=(.55,.65,.68)
            comparison[reference&~model,:3]=(1,.12,.12);comparison[model&~reference,:3]=(.05,.25,1)
            image_save(out/f'comparison_{view}.png',comparison)
        config=project.data['validation']
        baseline=config['baseline_iou']
        report={'status':'PASS' if all(r['status']=='PASS' for r in results.values()) else 'FAIL',
                'source_blend_sha256':digest_file(bpy.data.filepath),'views':results,
                'baseline_delta':{v:round(r['iou']-baseline[v],6) for v,r in results.items()},
                'method':'Actual opaque geometry renders from calibrated fixed cameras, no per-view fitting',
                'source_mask_method':traces['method'],'label':label,'input_state_hash':model_inputs_hash(project,scope=label)}
        write_json(project.path(f'validation/{label}_migration_report.json'),report)
        require(results,baseline,config['max_iou_regression'])
        return report
    finally:
        scene.world=oldworld;scene.view_layers[0].material_override=None
        for name,hidden in saved.items():
            if name in bpy.data.objects:bpy.data.objects[name].hide_render=hidden
