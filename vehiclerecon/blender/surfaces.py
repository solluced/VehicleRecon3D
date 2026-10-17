import bpy,bmesh
from mathutils import Vector
from ..surfaces.builder import Graph
from ..surfaces.patches import grid,parameters
from ..surfaces.topology import valid_schedule
from .geometry import mesh
from .materials import material
from .scene import save

def cage_curves():
    return {o.name:[{'co':p.co.copy(),'left':p.handle_left.copy(),'right':p.handle_right.copy()} for p in o.data.splines[0].bezier_points]
            for o in bpy.data.objects if o.type=='CURVE'}

def finish(obj,config):
    target=Vector(config['normal'])
    if sum(p.normal.dot(target) for p in obj.data.polygons)<0:
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    if config['mirror']:
        mod=obj.modifiers.new('Symmetry','MIRROR');mod.use_axis[0]=False;mod.use_axis[1]=True;mod.use_clip=True;mod.merge_threshold=config['merge_threshold']
    if config['subdivision']:
        mod=obj.modifiers.new('Surface refinement','SUBSURF');mod.levels=1;mod.render_levels=config['subdivision']
    mod=obj.modifiers.new('Panel thickness','SOLIDIFY');mod.thickness=config['thickness'];mod.offset=-1
    return obj

def build(project):
    config=project.generated('surface_graph',check=False)
    for entry in config['materials']:material(entry)
    from ..authoring.workspace import Workspace
    workspace=Workspace(project.root) if project.data['schema_version']==2 else None
    if workspace is not None:
        from ..authoring.reviews import require_acceptance
        require_acceptance(workspace)
    graph=Graph(config,cage_curves(),Vector,workspace=workspace)
    for patch in config['patches']:
        sample=graph.get(patch['sample']);settings={**config['settings'],**patch.get('settings',{})}
        us=patch.get('us') or parameters(patch['resolution'][0],settings['support'])
        vs=patch.get('vs') or parameters(patch['resolution'][1],settings['support'])
        if not patch.get('us') and settings['mirror'] and all(abs(sample(0,v).y)<1e-7 for v in (0,.5,1)):
            us.remove(settings['support'][0])
        if not patch.get('vs') and settings['mirror'] and all(abs(sample(u,0).y)<1e-7 for u in (0,.5,1)):
            vs.remove(settings['support'][0])
        valid_schedule(us);valid_schedule(vs)
        vertices,faces=grid(sample,us,vs)
        obj=mesh(patch['id'],vertices,faces,patch['material'],patch['collection'])
        obj['grid_us']=us;obj['grid_vs']=vs
        finish(obj,settings)
    for stitch in config['stitches']:
        obj=bpy.data.objects[stitch['surface']]
        us=list(obj['grid_us']);vs=list(obj['grid_vs']);n=len(us)
        indices=[i for i,u in enumerate(us) if stitch['u_range'][0]<=u<=stitch['u_range'][1]]
        target=graph.get(stitch['target'])
        top=[target(j/(len(indices)-1)) for j in range(len(indices))]
        bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table()
        bottom=[bm.verts[(len(vs)-1)*n+i] for i in indices];previous=bottom
        for fraction in stitch['rows']:
            row=[bm.verts.new(a.co.lerp(b,fraction)) for a,b in zip(bottom,top)]
            for j in range(len(row)-1):
                face=bm.faces.new((previous[j],previous[j+1],row[j+1],row[j]));face.normal_update()
                if face.normal.dot(Vector(stitch['normal']))<0:face.normal_flip()
            previous=row
        bm.to_mesh(obj.data);bm.free();obj.data.update()
    from .primitives import build_blockout
    if 'blockout' in config:build_blockout(project,config['blockout'])
    lighting(project)
    save(project.path('.cache/surfaces.blend'))

def lighting(project):
    from .collections import ensure
    from .cameras import aim
    for entry in project.data['presentation']['lights']:
        data=bpy.data.lights.new(entry['name'],'AREA');data.energy=entry['power'];data.shape='DISK';data.size=entry['size']
        obj=bpy.data.objects.new(entry['name'],data);ensure('09_PRESENTATION').objects.link(obj);obj.location=entry['position'];aim(obj,entry['target'])
