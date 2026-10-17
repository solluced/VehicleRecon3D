"""Bounded graph contracts and typed mutations shared by headless and Studio users."""
import copy
from ..core.project import RESOURCE_ROOT, read_json, validate
from ..core.errors import SchemaError, ReferenceError
from .builder import OPERATIONS, order

INPUTS = {'curve_sample':['curve'], 'lerp':['a','b'], 'offset':['source'],
          'coons':['bottom','top','left','right'], 'cubic_boundary_roll':['inner','outer'], 'ribbon':['curve']}
SURFACES = {'coons','cubic_boundary_roll','arch_annulus','ribbon','bilinear_patch'}
COMMANDS = {'AddSurfacePatch','DeleteSurfacePatch','AddSurfaceNode','DeleteSurfaceNode',
            'SetSurfaceOperation','SetSurfaceParameter','SetSurfaceBoundary','ReverseSurfaceBoundary',
            'SetSurfaceDraft','SetSurfaceResolution','SetSurfaceMaterialRole','SetSurfaceMirror',
            'SetSurfaceNormal','AddSurfaceSupport','RemoveSurfaceSupport','SetSurfaceAdjacency'}


def registry():
    """Parameter schemas are the production contracts, never a UI-owned palette."""
    schema=read_json(RESOURCE_ROOT/'schemas/surface_graph.schema.json')
    result=[]
    for node in schema['properties']['nodes']['items']['oneOf']:
        p=node['properties'];op=p['op']['const'];params=p['parameters'];inputs=INPUTS.get(op,[])
        result.append({'id':op,'version':1,'description':op.replace('_',' '),
            'parameter_schema':params,'required_inputs':[x for x in inputs if x in params.get('required',[])],
            'optional_inputs':[x for x in inputs if x not in params.get('required',[])],
            'output_type':'surface' if op in SURFACES or op=='lerp' else 'mesh' if op=='boundary_stitch' else 'point' if op=='curve_sample' else 'curve_or_point' if op=='offset' else 'curve',
            'dimensional_expectations':'World coordinates and offsets in metres; normalized parameters in [0,1].',
            'preview_supported':op!='boundary_stitch','topology_supported':op in SURFACES or op=='lerp',
            'limitation':'Discrete boundary_stitch has no callable surface domain.' if op=='boundary_stitch' else None})
    if {r['id'] for r in result}!=OPERATIONS:raise SchemaError('Operation metadata does not match trusted evaluator')
    return {'operations':result,'capabilities':{'mirror':True,'mirror_plane':'Y=0 (existing Blender symmetry)',
        'support_rows':'Explicit U/V sampling schedules; no independent strength parameter.',
        'patch_boundary_extraction':False,'patch_boundary_reason':'No trusted core boundary extraction operation.',
        'self_intersection':'Deferred to Blender geometry audit.',
        'cage_boundaries':'bezier_rail_range: VECTOR handles, strictly increasing X; AUTO requires Blender.'}}


def empty_graph():
    return {'schema_version':2,'nodes':[],'patches':[],'stitches':[], 'adjacency':[],
        'settings':{'support':[.012,.988],'normal':[0,0,1],'mirror':False,'merge_threshold':.001,'subdivision':1,'thickness':.002},
        'materials':[{'name':'SURFACE','kind':'principled','color':[.3,.45,.6],'metallic':0,'roughness':.4}]}


def dependencies(node):
    return sorted({node['parameters'][k] for k in INPUTS.get(node['op'],[]) if k in node['parameters']})


def graph_contract(config, cage=None):
    """Drafts may omit inputs, but never store cycles, bad types or unknown refs."""
    validate(config,'surface_graph')
    nodes={n['id']:n for n in config['nodes']};patches={p['id']:p for p in config['patches']}
    if len(patches)!=len(config['patches']):raise SchemaError('Duplicate patch ID')
    ordered=order(config['nodes'])
    kinds={}
    for n in ordered:
        if n['dependencies']!=dependencies(n):raise SchemaError('Dependencies must match operation inputs: '+n['id'])
        if set(n.get('reversed',[]))-set(INPUTS.get(n['op'],[])):raise SchemaError('Unsupported boundary orientation')
        if n['op']=='bezier_rail_range' and cage is not None:
            if n['parameters'].get('curve') not in {c['id'] for c in cage['curves']}:raise ReferenceError('Unknown cage boundary')
        for k in ('t',):
            if k in n['parameters'] and not 0<=n['parameters'][k]<=1:raise SchemaError('Normalized parameter outside [0,1]')
        if n['op']=='bezier_rail_range' and 'x_range' in n['parameters'] and n['parameters']['x_range'][0]==n['parameters']['x_range'][1]:raise SchemaError('Empty rail range')
        op=n['op'];params=n['parameters'];inputs={k:kinds[v] for k,v in params.items() if k in INPUTS.get(op,[]) and v in kinds}
        if op in ('coons','cubic_boundary_roll','ribbon','curve_sample') and any(v!='curve' for v in inputs.values()):raise SchemaError('Operation requires curve inputs: '+n['id'])
        if op=='lerp':
            if len(set(inputs.values()))>1 or any(v not in ('curve','point') for v in inputs.values()):raise SchemaError('lerp requires two curves or two points')
            kinds[n['id']]='surface' if 'curve' in inputs.values() else 'point'
        elif op=='offset':
            if any(v not in ('curve','point') for v in inputs.values()):raise SchemaError('offset requires curve or point')
            kinds[n['id']]=next(iter(inputs.values()),'curve')
        else:kinds[n['id']]='surface' if op in SURFACES else 'point' if op=='curve_sample' else 'mesh' if op=='boundary_stitch' else 'curve'
    for p in patches.values():
        if p['sample'] not in nodes:raise ReferenceError('Unknown patch sample')
        if kinds[p['sample']]!='surface' and not (nodes[p['sample']].get('draft') and nodes[p['sample']]['op']=='lerp'):raise SchemaError('Patch requires a surface operation')
        from .topology import valid_schedule
        for key in ('us','vs'):
            if key in p:valid_schedule(p[key])
        normal=p['settings'].get('normal',config['settings']['normal'])
        if sum(x*x for x in normal)<1e-20:raise SchemaError('Normal direction cannot be zero')
    for a in config.get('adjacency',[]):
        if a['a'] not in patches or a['b'] not in patches or a['a']==a['b']:raise ReferenceError('Invalid adjacency patch identity')
    return ordered


def mutate(workspace, command):
    c=command;op=c['type'];docs=workspace.documents
    if 'surface_graph' not in docs:
        docs['surface_graph']=empty_graph();docs['project']['generated']['surface_graph']='generated/surface_graph.json'
    g=docs['surface_graph']
    if g['schema_version']!=2:raise SchemaError('Legacy surface graph is read-only; explicit surface migration required')
    def find(group,key):
        item=next((v for v in g[group] if v['id']==c[key]),None)
        if item is None:raise ReferenceError('Surface identity missing: '+c[key])
        return item
    if op in ('AddSurfaceNode','AddSurfacePatch'):
        if any(n['id']==c['node_id'] for n in g['nodes']):raise SchemaError('Duplicate node ID')
        g['nodes'].append({'id':c['node_id'],'op':c['op'],'parameters':{},'dependencies':[],'draft':True,'reversed':[]})
        if op=='AddSurfacePatch':
            if any(p['id']==c['patch_id'] for p in g['patches']):raise SchemaError('Duplicate patch ID')
            g['patches'].append({'id':c['patch_id'],'sample':c['node_id'],'name':c['name'],'semantic_role':c['semantic_role'],
                'resolution':[8,8],'material':'SURFACE','material_role':'generic','collection':'02_SURFACES','settings':{}})
    elif op=='DeleteSurfacePatch':
        p=find('patches','patch_id');g['patches'].remove(p)
        g['adjacency']=[a for a in g.get('adjacency',[]) if c['patch_id'] not in (a['a'],a['b'])]
    elif op=='DeleteSurfaceNode':g['nodes'].remove(find('nodes','node_id'))
    elif op=='SetSurfaceAdjacency':g['adjacency']=copy.deepcopy(c['adjacency'])
    elif 'node_id' in c:
        n=find('nodes','node_id')
        if op=='SetSurfaceOperation':n.update(op=c['op'],parameters={},dependencies=[],draft=True,reversed=[])
        elif op=='SetSurfaceDraft':n['draft']=c['draft']
        elif op in ('SetSurfaceParameter','SetSurfaceBoundary'):
            key=c.get('parameter',c.get('boundary'));value=c.get('value',c.get('source'))
            if op=='SetSurfaceBoundary' and key not in INPUTS.get(n['op'],[]):raise SchemaError('Unsupported boundary slot')
            n['parameters'][key]=copy.deepcopy(value)
            validate(g,'surface_graph')
            n['dependencies']=dependencies(n)
        elif op=='ReverseSurfaceBoundary':
            key=c['boundary']
            if key not in INPUTS.get(n['op'],[]):raise SchemaError('Unsupported boundary orientation')
            reversed_=n.setdefault('reversed',[])
            reversed_.remove(key) if key in reversed_ else reversed_.append(key)
    else:
        p=find('patches','patch_id')
        if op=='SetSurfaceResolution':p['resolution']=c['resolution']
        elif op=='SetSurfaceMaterialRole':p['material_role']=c['material_role']
        elif op=='SetSurfaceMirror':p['settings']['mirror']=c['enabled']
        elif op=='SetSurfaceNormal':p['settings']['normal']=c['normal']
        elif op in ('AddSurfaceSupport','RemoveSurfaceSupport'):
            key='us' if c['axis']=='u' else 'vs';index=0 if key=='us' else 1
            values=p.setdefault(key,[i/p['resolution'][index] for i in range(p['resolution'][index]+1)])
            if op=='AddSurfaceSupport':values[:]=sorted(set([*values,c['position']]))
            elif c['position'] in values:values.remove(c['position'])
            else:raise ReferenceError('Support sample missing')
    graph_contract(g,docs.get('cage'))
    return 'surface_graph'
