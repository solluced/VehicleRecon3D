import bpy
from .materials import material
from .collections import ensure,link
from .cameras import camera
from .scene import render,save

def build(project):
    config=project.data['presentation']
    for entry in config['materials']:material(entry)
    style=config['wire']
    for name in config['wire_sources']:
        source=bpy.data.objects[name];obj=source.copy();obj.data=source.data.copy();ensure(style['collection']).objects.link(obj);obj.name=style['prefix']+name
        for mod in list(obj.modifiers):
            if mod.type!='MIRROR':obj.modifiers.remove(mod)
        obj.data.materials.clear();obj.data.materials.append(bpy.data.materials[style['material']])
        wrap=obj.modifiers.new('Follow actual refined surface','SHRINKWRAP');wrap.target=source;wrap.wrap_method='NEAREST_SURFACEPOINT';wrap.offset=style['offset']
        mod=obj.modifiers.new('Real mesh edge overlay','WIREFRAME');mod.thickness=style['thickness'];mod.offset=1;mod.use_replace=True;mod.use_boundary=True
        obj['source_topology_object']=source.name
    ground=config['ground']
    bpy.ops.mesh.primitive_plane_add(size=ground['size'],location=ground['position']);obj=bpy.context.object;obj.name=ground['name'];link(obj,ground['collection']);obj.data.materials.append(bpy.data.materials[ground['material']])
    camera(config['camera'],'09_PRESENTATION')
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=config['samples'];scene.view_settings.view_transform='AgX'
    scene.camera=bpy.data.objects[config['camera']['name']]
    for image in bpy.data.images:
        if image.name.startswith(('reference_','REF_CROP_')):
            image.use_fake_user=True
            if image.source=='FILE':image.pack()
    save(project.blend)
    render_views(project)
    diagnostics(project)

def render_views(project):
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=project.data['presentation']['samples'];scene.view_settings.view_transform='AgX'
    for record in project.data['presentation']['views']:
        render(project.path('validation/'+record['view']+'.png'),record['camera'],*record['size'])

def diagnostics(project):
    scene=bpy.context.scene;config=project.data['presentation'];visibility={o.name:o.hide_render for o in bpy.data.objects}
    for obj in bpy.data.objects:
        if obj.get('source_topology_object'):obj.hide_render=True
    width,height=config['diagnostic_size'];camera_id=config['camera']['name']
    render(project.path('validation/perspective_surface.png'),camera_id,width,height)
    mat=bpy.data.materials.new('REFLECTION_DIAGNOSTIC');mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear()
    tex=nodes.new('ShaderNodeTexCoord');wave=nodes.new('ShaderNodeTexWave');wave.wave_type='BANDS';wave.bands_direction='X';wave.inputs['Scale'].default_value=5
    ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.43;ramp.color_ramp.elements[1].position=.57
    ramp.color_ramp.elements[0].color=(.015,.015,.015,1);ramp.color_ramp.elements[1].color=(.9,.9,.9,1)
    shader=nodes.new('ShaderNodeBsdfPrincipled');shader.inputs['Roughness'].default_value=.15;shader.inputs['Metallic'].default_value=.3;out=nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(tex.outputs['Reflection'],wave.inputs['Vector']);mat.node_tree.links.new(wave.outputs['Color'],ramp.inputs[0]);mat.node_tree.links.new(ramp.outputs[0],shader.inputs['Base Color']);mat.node_tree.links.new(shader.outputs[0],out.inputs[0])
    original={}
    for collection in project.data['validation']['geometry']['surface_collections']:
        for obj in bpy.data.collections[collection].objects:
            if obj.type!='MESH' or obj.get('source_topology_object'):continue
            original[obj.name]=list(obj.data.materials);obj.data.materials.clear();obj.data.materials.append(mat)
    render(project.path('validation/surface_reflections.png'),camera_id,width,height)
    for name,materials in original.items():
        obj=bpy.data.objects[name];obj.data.materials.clear()
        for item in materials:obj.data.materials.append(item)
    for obj in bpy.data.collections[config['ground']['collection']].objects:
        if obj.type!='CAMERA':obj.hide_render=True
    scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='MATCAP';scene.display.shading.studio_light='metal_carpaint.exr'
    scene.display.shading.color_type='SINGLE';scene.display.shading.single_color=(.65,.65,.65);scene.display.shading.show_shadows=False;scene.display.shading.show_cavity=False;scene.display.shading.background_type='WORLD'
    render(project.path('validation/surface_matcap.png'),camera_id,width,height)
    for name,hidden in visibility.items():
        if name in bpy.data.objects:bpy.data.objects[name].hide_render=hidden
