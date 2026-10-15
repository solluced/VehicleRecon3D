"""GLB integrity and evaluated-source comparison, without Blender."""
import json,struct,math
from pathlib import Path
from ..core.errors import GateError
from ..core.manifest import digest_file,write_json
from ..core.project import read_json

IDENTITY=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]

def mul(a,b):return [sum(a[k*4+r]*b[c*4+k] for k in range(4)) for c in range(4) for r in range(4)]

def local(node):
    if 'matrix' in node:return node['matrix']
    x,y,z,w=node.get('rotation',[0,0,0,1]);sx,sy,sz=node.get('scale',[1,1,1]);tx,ty,tz=node.get('translation',[0,0,0])
    return [(1-2*y*y-2*z*z)*sx,(2*x*y+2*z*w)*sx,(2*x*z-2*y*w)*sx,0,(2*x*y-2*z*w)*sy,(1-2*x*x-2*z*z)*sy,(2*y*z+2*x*w)*sy,0,(2*x*z+2*y*w)*sz,(2*y*z-2*x*w)*sz,(1-2*x*x-2*y*y)*sz,0,tx,ty,tz,1]

class GLB:
    def __init__(self,path):
        raw=Path(path).read_bytes()
        if len(raw)<28 or struct.unpack_from('<III',raw)!=(0x46546c67,2,len(raw)):
            raise GateError('Invalid GLB header/length/version')
        length,kind=struct.unpack_from('<II',raw,12)
        if kind!=0x4e4f534a:raise GateError('Missing GLB JSON chunk')
        self.data=json.loads(raw[20:20+length]);offset=20+length
        if offset+8>len(raw):raise GateError('Missing GLB binary header')
        size,kind=struct.unpack_from('<II',raw,offset)
        if kind!=0x004e4942 or offset+8+size!=len(raw):raise GateError('Invalid GLB binary chunk')
        self.binary=memoryview(raw)[offset+8:]

    def accessor(self,index):
        item=self.data['accessors'][index]
        if 'sparse' in item or 'bufferView' not in item:raise GateError('Unsupported sparse/external accessor')
        view=self.data['bufferViews'][item['bufferView']]
        if view.get('buffer',0)!=0:raise GateError('External GLB buffer')
        components={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}
        formats={5120:'b',5121:'B',5122:'h',5123:'H',5125:'I',5126:'f'}
        if item['type'] not in components or item['componentType'] not in formats:raise GateError('Unsupported accessor format')
        fmt='<'+formats[item['componentType']]*components[item['type']]
        width=struct.calcsize(fmt);stride=view.get('byteStride',width)
        start=view.get('byteOffset',0)+item.get('byteOffset',0)
        if item['count']<1 or stride<width or start+(item['count']-1)*stride+width>view.get('byteOffset',0)+view['byteLength'] or view.get('byteOffset',0)+view['byteLength']>len(self.binary):
            raise GateError('Accessor outside binary/view bounds')
        return [struct.unpack_from(fmt,self.binary,start+i*stride) for i in range(item['count'])]

    def geometry(self):
        result={};active=set()
        def walk(index,parent):
            if index in active:raise GateError('GLB node cycle')
            active.add(index);node=self.data['nodes'][index];world=mul(parent,local(node))
            if 'mesh' in node:
                points=[];triangles=0
                for primitive in self.data['meshes'][node['mesh']]['primitives']:
                    if primitive.get('mode',4)!=4:raise GateError('GLB primitive is not triangles')
                    positions=self.accessor(primitive['attributes']['POSITION'])
                    indices=self.accessor(primitive['indices']) if 'indices' in primitive else [(i,) for i in range(len(positions))]
                    if len(indices)%3 or any(i[0]<0 or i[0]>=len(positions) for i in indices):raise GateError('Invalid triangle indices')
                    if 'NORMAL' not in primitive['attributes']:raise GateError('Missing exported normals')
                    normals=self.accessor(primitive['attributes']['NORMAL'])
                    if len(normals)!=len(positions) or any(not math.isfinite(n) for v in normals for n in v):raise GateError('Invalid normals')
                    triangles+=len(indices)//3
                    for point in positions:
                        points.append(tuple(sum(world[k*4+r]*point[k] for k in range(3))+world[12+r] for r in range(3)))
                if not points or any(not math.isfinite(n) for p in points for n in p):raise GateError('Empty/nonfinite exported geometry')
                name=node.get('name',str(index))
                if name in result:raise GateError('Duplicate exported mesh name')
                result[name]={'triangles':triangles,'bounds_min':[min(p[i] for p in points) for i in range(3)],'bounds_max':[max(p[i] for p in points) for i in range(3)]}
            for child in node.get('children',[]):walk(child,world)
            active.remove(index)
        for index in self.data['scenes'][self.data.get('scene',0)]['nodes']:walk(index,IDENTITY)
        return result

def verify(project):
    manifest=read_json(project.path('output/export_manifest.json',exists=True))
    if manifest['glb_sha256']!=digest_file(project.glb):raise GateError('GLB digest differs from export manifest')
    observed=GLB(project.glb).geometry();checks=[]
    for name,source in manifest['source_geometry'].items():
        actual=observed.get(name)
        error=max(abs(a-b) for key in ('bounds_min','bounds_max') for a,b in zip(source[key],actual[key])) if actual else None
        checks.append({'object':name,'pass':bool(actual and actual['triangles']==source['triangles'] and error<project.data['validation']['bounds_tolerance_m']),
                       'source_triangles':source['triangles'],'glb_triangles':actual['triangles'] if actual else None,'max_bounds_error_m':error})
    passed=all(c['pass'] for c in checks) and len(observed)==len(checks)
    result={'status':'PASS' if passed else 'FAIL','glb_sha256':manifest['glb_sha256'],'source_blend_sha256':manifest['source_blend_sha256'],
            'geometry_hash':manifest['geometry_hash'],'mesh_nodes':len(observed),'triangles':sum(v['triangles'] for v in observed.values()),'objects':checks}
    write_json(project.path('validation/glb_geometry_report.json'),result)
    if not passed:raise GateError('GLB differs from evaluated Blender geometry')
    return result
