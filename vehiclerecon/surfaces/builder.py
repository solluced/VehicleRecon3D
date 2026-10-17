"""Bounded, acyclic surface operation graph. No executable project expressions."""
from .curves import Vector,polyline,chord_hermite,shape_preserving_hermite,bezier_rail_range
from .coons import coons,bilinear_patch
from .patches import cubic_boundary_roll,ribbon,arch_annulus,boundary_stitch
from ..core.errors import ReferenceError,SchemaError

OPERATIONS={'polyline','chord_hermite','shape_preserving_hermite','bezier_rail_range',
            'curve_sample','lerp','offset','coons','cubic_boundary_roll','arch_annulus',
            'ribbon','bilinear_patch','boundary_stitch'}

def order(nodes):
    by_id={n['id']:n for n in nodes}
    if len(by_id)!=len(nodes):raise SchemaError('Duplicate graph ID')
    result=[];active=set();visited=set()
    def visit(name):
        if name not in by_id:raise ReferenceError(f'Unknown surface node {name}')
        if name in active:raise SchemaError('Surface graph cycle')
        if name in visited:return
        active.add(name)
        for dep in by_id[name]['dependencies']:visit(dep)
        active.remove(name);visited.add(name);result.append(by_id[name])
    for name in by_id:visit(name)
    return result

class Graph:
    def __init__(self,config,curves=None,vector=Vector,*,workspace=None,cache=None,identity=''):
        if config.get('schema_version')==2:
            from ..authoring.reviews import require_acceptance
            from .authoring import graph_contract
            from ..core.errors import BlockedError
            if workspace is None:raise BlockedError('v2 evaluation requires current accepted source/cage workspace')
            require_acceptance(workspace)
            graph_contract(config,workspace.documents.get('cage'))
            if any(n.get('draft') for n in config['nodes']):raise BlockedError('DRAFT / INCOMPLETE graph cannot execute')
        self.values={};self.vector=vector;self.curves=curves or {};self.keys={};self.evaluated=[];self.corners={}
        for node in order(config['nodes']):
            if node['op'] not in OPERATIONS:raise SchemaError(f"Unsupported operation {node['op']}")
            from ..core.manifest import digest_data
            key=digest_data([identity,node,[self.keys[d] for d in node['dependencies']]])
            self.keys[node['id']]=key
            if cache is not None and key in cache:
                self.values[node['id']]=cache[key];cache.move_to_end(key)
            else:
                self.values[node['id']]=self.evaluate(node);self.evaluated.append(node['id'])
                if cache is not None:
                    cache[key]=self.values[node['id']]
                    while len(cache)>256:cache.popitem(last=False)
        for patch in config.get('patches',[]):
            self.get(patch['sample'])

    def get(self,name):
        if name not in self.values:raise ReferenceError(f'Unknown surface reference {name}')
        return self.values[name]

    def evaluate(self,node):
        op=node['op'];p=node['parameters'];v=self.vector
        def boundary(key):
            value=self.get(p[key])
            return (lambda t:value(1-t)) if key in node.get('reversed',[]) else value
        if op=='polyline':return polyline(p['points'],v)
        if op=='chord_hermite':return chord_hermite(p['points'],v)
        if op=='shape_preserving_hermite':return shape_preserving_hermite(p['points'],v,p.get('endpoint_epsilon',0))
        if op=='bezier_rail_range':
            if p['curve'] not in self.curves:raise ReferenceError(f"Unknown cage curve {p['curve']}")
            return bezier_rail_range(self.curves[p['curve']],*p['x_range'])
        if op=='curve_sample':return self.get(p['curve'])(p['t'])
        if op=='lerp':
            a,b=self.get(p['a']),self.get(p['b'])
            if callable(a):return lambda u,t:a(u).lerp(b(u),t)
            return a.lerp(b,p['t'])
        if op=='offset':
            source=self.get(p['source']);offset=v(p['offset'])
            return (lambda t:source(t)+offset) if callable(source) else source+offset
        if op=='coons':
            from .coons import corner_report
            args=(boundary('bottom'),boundary('top'),boundary('left') if p.get('left') else None,boundary('right') if p.get('right') else None,p.get('corner_tolerance',1e-6))
            self.corners[node['id']]=corner_report(*args)
            return coons(*args)
        if op=='cubic_boundary_roll':return cubic_boundary_roll(boundary('inner'),boundary('outer'),p['first_control_scale'],p['second_scale'],p['slopes'],v)
        if op=='ribbon':return ribbon(boundary('curve'),p['start_offset'],p['end_offset'],v)
        if op=='bilinear_patch':return bilinear_patch(p['points'],v)
        if op=='arch_annulus':return arch_annulus(p['inner_points'],p['outer_points'],p['first_control_scale'],p['second_scale'],p['slopes'],v)
        if op=='boundary_stitch':return boundary_stitch(list(map(v,p['bottom'])),list(map(v,p['top'])),p['rows'])
        raise SchemaError(f'Unimplemented surface operation {op}')
