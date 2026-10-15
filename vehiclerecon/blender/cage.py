import bpy
import hashlib,json
from ..cage.builder import records
from ..core.manifest import write_json
from .geometry import curve
from .materials import material
from .scene import render,save

def build(project):
    config,entries=records(project,validate=False)
    for style in config['materials']:material(style)
    for entry in entries:
        curve(entry['id'],entry['points'],entry['material'],entry['radius'],config['collection'],entry['cyclic'],entry['handles'])
    bpy.context.view_layer.update()
    inventory=[]
    for obj in bpy.data.collections[config['collection']].objects:
        payload=[{'cyclic':sp.use_cyclic_u,'bezier':[{'co':list(p.co),'left':list(p.handle_left),'right':list(p.handle_right)} for p in sp.bezier_points]} for sp in obj.data.splines]
        inventory.append({'name':obj.name,'curve_sha256':hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()})
    write_json(project.path('validation/cage_inventory.json'),{'objects':inventory,'count':len(inventory)})
    scene=bpy.context.scene
    scene.cycles.samples=1
    scene.view_settings.view_transform='Standard'
    for view in config['renders']:
        render(project.path('validation/cage_'+view['view']+'.png'),view['camera'],*view['size'])
        if view['reference']:
            obj=bpy.data.objects[view['reference']];obj.hide_render=False
            render(project.path('validation/cage_overlay_'+view['view']+'.png'),view['camera'],*view['size'])
            obj.hide_render=True
    for obj in bpy.data.collections[config['collection']].objects:
        obj.hide_render=True;obj.hide_set(True)
    save(project.path('.cache/cage.blend'))
