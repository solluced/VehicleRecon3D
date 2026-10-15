import bpy

def material(config):
    name = config['name']
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_fake_user = True
    if config.get('kind') == 'emission':
        nodes = mat.node_tree.nodes
        nodes.clear()
        shader = nodes.new('ShaderNodeEmission')
        shader.inputs['Color'].default_value = (*config['color'], 1)
        shader.inputs['Strength'].default_value = config.get('strength', 1)
        output = nodes.new('ShaderNodeOutputMaterial')
        mat.node_tree.links.new(shader.outputs[0], output.inputs[0])
    else:
        shader = mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*config['color'], 1)
        shader.inputs['Roughness'].default_value = config.get('roughness', .3)
        shader.inputs['Metallic'].default_value = config.get('metallic', 0)
        for key, value in config.get('inputs', {}).items():
            shader.inputs[key].default_value = value
        mat.diffuse_color = (*config['color'], 1)
    return mat
