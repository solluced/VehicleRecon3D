"""Analytical distorted source fixture; stdlib PNG, no optional core dependencies."""
import copy,json,shutil,struct,zlib
from vehiclerecon.core.project import REPOSITORY
from vehiclerecon.core.manifest import digest_file
from vehiclerecon.authoring.contracts import crop_identity
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.reference.rectification import PiecewiseMonotonicAxisWarp
from vehiclerecon.reference.transforms import CalibrationTransform

def prepare(root,*,source=(0,.3,.65,1),target=(0,.31,.64,1)):
    shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',root)
    cal=json.loads((root/'generated/calibration.json').read_text());cage=json.loads((root/'generated/cage.json').read_text())
    transform=CalibrationTransform(cal);warp=PiecewiseMonotonicAxisWarp(source,target)
    columns=[round(40+180*warp.inverse(i/10)) for i in range(11)]
    raw=b''.join(b'\0'+b''.join(bytes((125,151,166) if x in columns or y%32==0 else (241,245,247)) for x in range(256)) for y in range(256))
    def chunk(name,value):return struct.pack('>I',len(value))+name+value+struct.pack('>I',zlib.crc32(name+value)&0xffffffff)
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',256,256,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
    (root/'input/reference.png').write_bytes(png);sha=digest_file(root/'input/reference.png');cal['source_sha256']=sha
    cal['views']['top']['crop']=[40,0,220,256]
    for view,d in cal['views'].items():
        for o in d['landmarks']['observations']:
            o.update(source_sha256=sha,crop_id=crop_identity(o['reference_id'],d['crop']))
            if view=='top':o['pixel'][0]=40+180*warp.inverse((o['pixel'][0]-40)/180)
    template=copy.deepcopy(cal['views']['top']['landmarks']['observations'][0]);link=copy.deepcopy(cal['correspondences'][0]);anchors=[]
    pairs=sorted(set([*source,.15,.45,.8]))
    for i,x in enumerate(pairs):
        ident=f'rect_obs_{i}';name=f'rect_world_{i}';point=40+180*warp(x)
        cage['landmarks'][name]=list(transform.pixel_to_world('top',point,128))
        o={**copy.deepcopy(template),'id':ident,'pixel':[40+180*x,128]};cal['views']['top']['landmarks']['observations'].append(o)
        l={**copy.deepcopy(link),'id':f'rect_link_{i}','observation_id':ident,'observation_revision':1,'world_entity_id':name,
            'binding_type':'landmark','required':True,'tolerance_policy':{'metric':'euclidean_px','allowed_px':.25},'semantic_role':'roof'}
        cal['correspondences'].append(l);cal['authoring_policy']['critical_correspondence_ids'].append(l['id'])
        anchors.append({'id':f'anchor_{i}','semantic':'front_axle' if x==0 else 'rear_axle' if x==1 else name,
            'image':x,'world_normalized':warp(x),'role':'FIT' if x in source else 'HELD_OUT','locked':x in (0,1),
            'observation_id':ident,'confidence':1,'provenance':'Independent analytical fixture sample'})
    project=json.loads((root/'project.json').read_text());project.update(asset_name='rectification_positive',project_id='rectification_positive')
    project['dimensions']['wheelbase_m']=3.6
    for name,data in [('project.json',project),('generated/calibration.json',cal),('generated/cage.json',cage)]:
        (root/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    Workspace(root)
    return {'view':'top','gauge_view':'side','reference_role':'multiview','axis':'u','image_domain_px':[40,220],'affine_domain_px':[40,220],
        'anchors':anchors,'max_scale_change':.1,'allow_extrapolation':False}
