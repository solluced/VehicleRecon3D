"""Compare exported node triangle counts and world-space bounds to Blender."""
from pathlib import Path
import json,struct,math,hashlib
ROOT=Path(__file__).resolve().parents[1]
data=(ROOT/'exports/tesla_surface_model.glb').read_bytes()
assert struct.unpack_from('<III',data,0)==(0x46546c67,2,len(data))
length,kind=struct.unpack_from('<II',data,12);assert kind==0x4e4f534a
g=json.loads(data[20:20+length]);offset=20+length
length,kind=struct.unpack_from('<II',data,offset);assert kind==0x004e4942
binary=memoryview(data)[offset+8:offset+8+length]
manifest=json.loads((ROOT/'exports/export_manifest.json').read_text())
assert manifest['glb_sha256']==hashlib.sha256(data).hexdigest()
I=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
def mul(a,b):return [sum(a[k*4+r]*b[c*4+k] for k in range(4)) for c in range(4) for r in range(4)]
def local(n):
    if 'matrix' in n:return n['matrix']
    x,y,z,w=n.get('rotation',[0,0,0,1]);sx,sy,sz=n.get('scale',[1,1,1]);tx,ty,tz=n.get('translation',[0,0,0])
    return [(1-2*y*y-2*z*z)*sx,(2*x*y+2*z*w)*sx,(2*x*z-2*y*w)*sx,0,(2*x*y-2*z*w)*sy,(1-2*x*x-2*z*z)*sy,(2*y*z+2*x*w)*sy,0,(2*x*z+2*y*w)*sz,(2*y*z-2*x*w)*sz,(1-2*x*x-2*y*y)*sz,0,tx,ty,tz,1]
def points(index):
    a=g['accessors'][index];v=g['bufferViews'][a['bufferView']];assert a['componentType']==5126 and a['type']=='VEC3'
    start=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',12)
    return [struct.unpack_from('<fff',binary,start+i*stride) for i in range(a['count'])]
observed={}
def walk(index,parent):
    n=g['nodes'][index];world=mul(parent,local(n))
    if 'mesh' in n:
        p=[];tri=0
        for primitive in g['meshes'][n['mesh']]['primitives']:
            assert primitive.get('mode',4)==4
            tri+=(g['accessors'][primitive['indices']]['count'] if 'indices' in primitive else g['accessors'][primitive['attributes']['POSITION']]['count'])//3
            for q in points(primitive['attributes']['POSITION']):
                p.append(tuple(sum(world[k*4+r]*q[k] for k in range(3))+world[12+r] for r in range(3)))
        assert all(math.isfinite(v) for q in p for v in q)
        observed[n['name']]={'triangles':tri,'bounds_min':[min(q[i] for q in p) for i in range(3)],'bounds_max':[max(q[i] for q in p) for i in range(3)]}
    for child in n.get('children',[]):walk(child,world)
for index in g['scenes'][g.get('scene',0)]['nodes']:walk(index,I)
checks=[]
for name,source in manifest['source_geometry'].items():
    actual=observed.get(name)
    error=max(abs(a-b) for key in ('bounds_min','bounds_max') for a,b in zip(source[key],actual[key])) if actual else None
    checks.append({'object':name,'pass':bool(actual and actual['triangles']==source['triangles'] and error<.0001),'source_triangles':source['triangles'],'glb_triangles':actual['triangles'] if actual else None,'max_bounds_error_m':error})
passed=all(c['pass'] for c in checks) and len(observed)==len(checks)
result={'status':'PASS' if passed else 'FAIL','glb_sha256':manifest['glb_sha256'],'source_blend_sha256':manifest['source_blend_sha256'],'mesh_nodes':len(observed),'triangles':sum(v['triangles'] for v in observed.values()),'method':'Every exported node compared with evaluated Blender geometry: triangle count, finite positions and world-space bounds to 0.1mm. Browser embeds these exact GLB bytes.','objects':checks}
(ROOT/'validation/glb_geometry_report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='objects'},indent=2))
assert passed,'GLB geometry differs from the evaluated Blender model'
