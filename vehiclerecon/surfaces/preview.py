"""Core-owned, revision-bound coarse authoring feedback. No production certification."""
import copy
import math
import time
from collections import OrderedDict
from pathlib import Path
from ..core.errors import ReconError, SchemaError, BlockedError, ConflictError
from ..core.manifest import digest_data
from ..authoring.reviews import require_acceptance, review_status
from .authoring import graph_contract, empty_graph, INPUTS
from .builder import Graph
from .curves import Vector
from .patches import grid
from .coons import corner_report


def implementation_identity():
    import hashlib
    return hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path(__file__).parent.glob('*.py')))).hexdigest()


def cage_curves(workspace):
    from ..authoring.contracts import resolved_cage
    from ..cage.schema import expand
    cage=resolved_cage(workspace.documents.get('cage',{'curves':[],'landmarks':{}}))
    geometry=workspace.documents.get('calibration',{}).get('wheel_geometry',{'axles':[]})
    result={}
    for curve in expand(cage,geometry):
        if curve['handles']!='VECTOR' or curve.get('cyclic'):continue
        points=list(map(Vector,curve['points']))
        if any(a.x>=b.x for a,b in zip(points,points[1:])):continue
        result[curve['id']]=[{'co':p,'left':p+(points[max(0,i-1)]-p)/3,
                            'right':p+(points[min(len(points)-1,i+1)]-p)/3} for i,p in enumerate(points)]
    return result


def inspect(workspace):
    g=workspace.documents.get('surface_graph',empty_graph())
    reviews={k:review_status(workspace,k) for k in ('source','cage')}
    ready=all(r['state']=='READY' for r in reviews.values())
    eligible=cage_curves(workspace) if 'cage' in workspace.documents and 'calibration' in workspace.documents else {}
    return {'revision':workspace.revision,'graph':g,'reviews':reviews,'evaluation_allowed':ready,
        'gate':'READY' if ready else 'BLOCKED BY SOURCE/CAGE ACCEPTANCE',
        'cage_boundaries':[{'id':k,'x_range':[v[0]['co'].x,v[-1]['co'].x],
                            'points':[list(p['co']) for p in v]} for k,v in eligible.items()],
        'validation':validate_graph(workspace,g)}


def validate_graph(workspace, config):
    rows=[]
    try:
        graph_contract(config,workspace.documents.get('cage'))
        rows=[{'category':c,'status':'PASS','message':'Contract satisfied'} for c in ('schema','references','DAG','operation contract','parameters')]
        incomplete=[n['id'] for n in config['nodes'] if n.get('draft')]
        rows.append({'category':'boundaries','status':'INCOMPLETE' if incomplete else 'PASS',
                     'message':'DRAFT / INCOMPLETE: '+', '.join(incomplete) if incomplete else 'Assigned inputs are structurally valid; evaluate to inspect corners.'})
    except (ReconError,KeyError,TypeError,ValueError) as exc:
        rows=[{'category':'graph','status':'FAIL','message':str(exc)[:2000]}]
    return rows


def cross(a,b):return Vector((a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]))
def unit(v):return v/v.length if v.length>1e-20 else Vector((0,0,0))
def angle(a,b):return math.degrees(math.acos(max(-1,min(1,unit(a).dot(unit(b))))))


def sample_normal(sample,u,v):
    e=1e-5
    return unit(cross(sample(min(1,u+e),v)-sample(max(0,u-e),v),sample(u,min(1,v+e))-sample(u,max(0,v-e))))


def edge_uv(edge,t):return {'bottom':(t,0),'top':(t,1),'left':(0,t),'right':(1,t)}[edge]


def adjacency(config):
    """Connectivity comes from declarations or shared canonical boundary IDs."""
    rows=copy.deepcopy(config.get('adjacency',[]));seen={(a['a'],a['edge_a'],a['b'],a['edge_b']) for a in rows}
    boundaries={};nodes={n['id']:n for n in config['nodes']}
    for p in config['patches']:
        n=nodes[p['sample']]
        if n['op']!='coons':continue
        for edge in ('bottom','top','left','right'):
            if edge in n['parameters']:boundaries.setdefault(n['parameters'][edge],[]).append((p['id'],edge,edge in n.get('reversed',[])))
    for values in boundaries.values():
        for i,a in enumerate(values):
            for b in values[i+1:]:
                key=(a[0],a[1],b[0],b[1])
                if a[0]!=b[0] and key not in seen and (b[0],b[1],a[0],a[1]) not in seen:
                    rows.append({'a':a[0],'edge_a':a[1],'b':b[0],'edge_b':b[1],'reverse':a[2]!=b[2],'tolerance_m':1e-6});seen.add(key)
    return rows


class PreviewCache:
    """Bounded derived functions/meshes; acceptance and validation run on every request."""
    def __init__(self):self.nodes=OrderedDict();self.meshes=OrderedDict();self.bytes=0
    def metrics(self):return {'nodes':len(self.nodes),'node_limit':256,'mesh_entries':len(self.meshes),'mesh_bytes':self.bytes,'mesh_limit_bytes':16*1024*1024}
    def put(self,key,value):
        import json
        size=len(json.dumps(value,allow_nan=False).encode())
        if size>16*1024*1024:return
        if key in self.meshes:self.bytes-=self.meshes.pop(key)[1]
        self.meshes[key]=(copy.deepcopy(value),size);self.bytes+=size
        while len(self.meshes)>64 or self.bytes>16*1024*1024:
            _,(_,old)=self.meshes.popitem(last=False);self.bytes-=old


def evaluate(workspace, *, config=None, expected_revision=None, quality='low', cache=None):
    started=time.perf_counter()
    from ..core.revisions import revision
    if revision(workspace.root)!=workspace.revision or (expected_revision is not None and expected_revision!=workspace.revision):raise ConflictError('Preview inputs are stale')
    require_acceptance(workspace)
    if quality not in ('low','medium'):raise SchemaError('Preview quality must be low or medium')
    g=copy.deepcopy(config if config is not None else workspace.documents.get('surface_graph',empty_graph()))
    if g.get('schema_version')!=2:raise BlockedError('Legacy graph preview requires explicit v2 authoring contract')
    graph_contract(g,workspace.documents.get('cage'))
    if not g['patches']:raise BlockedError('No surface patches authored')
    if g.get('stitches') or any(n['op']=='boundary_stitch' for n in g['nodes']):raise BlockedError('Discrete boundary_stitch preview is unsupported; use Blender for this graph')
    if len(g['patches'])>256 or len(g['nodes'])>2048:raise SchemaError('Coarse preview budget exceeded')
    identity=digest_data([implementation_identity(),workspace.documents.get('cage'),workspace.documents.get('calibration')])
    result={'revision':workspace.revision,'graph_hash':digest_data(g),'identity':identity,'quality':quality,
        'label':'COARSE AUTHORING PREVIEW','topology_label':'preview topology','authority':'Blender owns final geometry; no Class-A or game-ready certification.',
        'self_intersection':'NOT TESTED — deferred to Blender geometry audit','patches':[],'corners':{},'adjacency':[],
        'validation':validate_graph(workspace,g),'status':'PASS','evaluated_nodes':[],'sampled_patches':[],'boundaries':[]}
    graph=Graph.__new__(Graph)
    try:
        Graph.__init__(graph,g,cage_curves(workspace),workspace=workspace,cache=cache.nodes if cache else None,identity=identity)
        result['evaluated_nodes']=graph.evaluated
        for n in g['nodes']:
            if n['op'] in ('polyline','chord_hermite','shape_preserving_hermite','bezier_rail_range','offset'):
                value=graph.get(n['id'])
                if callable(value):
                    points=[list(value(i/32)) for i in range(33)]
                    from ..core.project import finite
                    finite(points);result['boundaries'].append({'id':n['id'],'points':points})
        for n in g['nodes']:
            if n['op']=='coons':
                def boundary(key):
                    if key not in n['parameters']:return None
                    value=graph.get(n['parameters'][key]);return (lambda t:value(1-t)) if key in n.get('reversed',[]) else value
                result['corners'][n['id']]=corner_report(*(boundary(k) for k in ('bottom','top','left','right')),n['parameters'].get('corner_tolerance',1e-6))
        for p in g['patches']:
            settings={**g['settings'],**p['settings']};key=digest_data([graph.keys[p['sample']],p,quality,settings])
            if cache and key in cache.meshes:
                mesh=copy.deepcopy(cache.meshes[key][0]);cache.meshes.move_to_end(key)
            else:
                sample=graph.get(p['sample']);limit=8 if quality=='low' else 16
                us=p.get('us') or [i/min(limit,p['resolution'][0]) for i in range(min(limit,p['resolution'][0])+1)]
                vs=p.get('vs') or [i/min(limit,p['resolution'][1]) for i in range(min(limit,p['resolution'][1])+1)]
                if len(us)*len(vs)>4225:raise SchemaError('Preview sample budget exceeded')
                vertices,quads=grid(sample,us,vs);triangles=[list(t) for a,b,c,d in quads for t in ((a,b,c),(a,c,d))]
                normals=[];face_normals=[];issues=[];normal_target=Vector(settings['normal']);positions=list(map(list,vertices))
                if not all(math.isfinite(x) for v in vertices for x in v):raise SchemaError('Nonfinite preview mesh')
                if len(set(map(tuple,positions)))!=len(vertices):issues.append('Duplicate vertices / self-collapsed patch')
                for t in triangles:
                    a,b,c=(vertices[i] for i in t);normal=cross(b-a,c-a);lengths=[(a-b).length,(b-c).length,(c-a).length]
                    if not math.isfinite(normal.length) or not all(math.isfinite(x) for x in lengths):raise SchemaError('Nonfinite triangle area or edge length')
                    if normal.length<1e-14:issues.append('Zero-area triangle')
                    if min(lengths)<1e-14 or max(lengths)/max(min(lengths),1e-20)>1e4:issues.append('Extreme triangle aspect ratio')
                    if normal.dot(normal_target)<-1e-14:issues.append('Reversed winding against expected normal')
                    face_normals.append({'origin':list((a+b+c)/3),'normal':list(unit(normal))})
                for v in vs:
                    for u in us:normals.append(list(sample_normal(sample,u,v)))
                mesh={'id':p['id'],'node_id':p['sample'],'operation':next(n['op'] for n in g['nodes'] if n['id']==p['sample']),
                    'positions':positions,'triangles':triangles,'normals':normals,'face_normals':face_normals,
                    'resolution':[len(us)-1,len(vs)-1],'semantic_role':p.get('semantic_role','generic'),
                    'material_role':p.get('material_role','generic'),'mirror':settings['mirror'],
                    'mirror_plane':'Y=0','mirror_counterpart':p['id']+'.mirror','issues':sorted(set(issues)),
                    'status':'FAIL' if issues else 'PASS'}
                if settings['mirror']:
                    offset=len(mesh['positions']);mesh['positions'] += [[x,-y,z] for x,y,z in positions]
                    mesh['triangles'] += [[c+offset,b+offset,a+offset] for a,b,c in list(mesh['triangles'])]
                    mesh['normals'] += [[x,-y,z] for x,y,z in list(mesh['normals'])]
                    mesh['face_normals'] += [{'origin':[f['origin'][0],-f['origin'][1],f['origin'][2]],'normal':[f['normal'][0],-f['normal'][1],f['normal'][2]]} for f in list(face_normals)]
                from ..core.project import finite
                finite(mesh)
                if cache:cache.put(key,mesh)
                result['sampled_patches'].append(p['id'])
            result['patches'].append(mesh)
        patches={p['id']:p for p in g['patches']}
        for item in adjacency(g):
            a=graph.get(patches[item['a']]['sample']);b=graph.get(patches[item['b']]['sample']);gaps=[];angles=[];points=[]
            for i in range(17):
                t=i/16;au,av=edge_uv(item['edge_a'],t);bu,bv=edge_uv(item['edge_b'],1-t if item['reverse'] else t)
                pa,pb=a(au,av),b(bu,bv);gaps.append((pa-pb).length);angles.append(angle(sample_normal(a,au,av),sample_normal(b,bu,bv)));points.append(list((pa+pb)/2))
            result['adjacency'].append({**item,'max_gap_m':max(gaps),'rms_gap_m':math.sqrt(sum(d*d for d in gaps)/len(gaps)),
                'normal_angle_max_deg':max(angles),'tangent_label':'G1-like normal compatibility; no strict G1/G2 guarantee',
                'status':'FAIL' if max(gaps)>item['tolerance_m'] else 'WARNING' if max(angles)>5 else 'PASS','samples':points})
        if any(p['status']=='FAIL' for p in result['patches']) or any(a['status']=='FAIL' for a in result['adjacency']):result['status']='FAIL'
        elif any(a['status']=='WARNING' for a in result['adjacency']):result['status']='WARNING'
        result['validation'] += [{'category':'evaluation','status':'PASS','message':'Core sampled graph'},
                                  {'category':'topology preview','status':result['status'],'message':'Numerical, winding and declared connectivity checks; self-intersection deferred.'}]
    except (ReconError,KeyError,ValueError,TypeError,OverflowError,ZeroDivisionError) as exc:
        corners=getattr(graph,'corners',{})
        from ..core.project import finite
        try:finite(corners)
        except SchemaError:corners={}
        result.update(status='FAIL',patches=[],boundaries=[],adjacency=[],corners=corners)
        result['validation'].append({'category':'evaluation','status':'BLOCKED','message':str(exc)[:2000]})
    from ..core.project import finite
    try:finite(result)
    except SchemaError:
        result.update(status='FAIL',patches=[],boundaries=[],adjacency=[],corners={})
        result['validation'].append({'category':'evaluation','status':'FAIL','message':'Nonfinite numerical output rejected'})
    if revision(workspace.root)!=workspace.revision:raise ConflictError('Preview inputs changed during evaluation')
    result['generation_ms']=(time.perf_counter()-started)*1000
    result['certified_current']=result['status'] in ('PASS','WARNING')
    return result
