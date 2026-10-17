"""Independent analytical v2 multi-view fixture and optional copied legacy diagnostic."""
import copy,json,shutil,sys
from pathlib import Path
from PIL import Image,ImageDraw
from vehiclerecon.core.project import REPOSITORY
from vehiclerecon.core.manifest import digest_file
from vehiclerecon.core.transactions import commit
from vehiclerecon.authoring.contracts import crop_identity
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.reference.transforms import CalibrationTransform

root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',root/'study')
if '--legacy' in sys.argv:
    source=REPOSITORY/'projects/mark2';target=root/'legacy_conflict';target.mkdir()
    shutil.copyfile(source/'project.json',target/'project.json')
    shutil.copytree(source/'input',target/'input');shutil.copytree(source/'generated',target/'generated')
    (target/'validation').mkdir()
    for name in ('cage_residuals.json','correction_reference_landmarks.json','reference_reconciliation_report.json','view_longitudinal_ratios.json','rectification_candidate.json','rectification_magnitude.json'):
        shutil.copyfile(source/'validation'/name,target/'validation'/name)
if '--performance' in sys.argv:
    target=root/'performance';shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',target)
    image=Image.new('RGB',(3840,2160),'#dce5e7');draw=ImageDraw.Draw(image)
    for x in range(0,3840,120):draw.line((x,0,x,2160),fill='#b9c9cf',width=2)
    for y in range(0,2160,120):draw.line((0,y,3840,y),fill='#b9c9cf',width=2)
    image.save(target/'input/reference4k.png');sha=digest_file(target/'input/reference4k.png')
    w=Workspace(target);cal=w.documents['calibration'];cage=w.documents['cage'];project=w.documents['project']
    project.update(asset_name='multiview_performance',project_id='multiview_performance');project['references']['multiview']='input/reference4k.png'
    cal.update(source='input/reference4k.png',source_size=[3840,2160],source_sha256=sha)
    for view,d in cal['views'].items():
        d['u_basis']=[v*256/3840 for v in d['u_basis']];d['v_basis']=[v*256/2160 for v in d['v_basis']];d['crop']=[0,0,3840,2160]
        d['landmarks']['body_bbox']=[v*(3840/256 if i%2==0 else 2160/256) for i,v in enumerate(d['landmarks']['body_bbox'])]
        for o in d['landmarks']['observations']:
            o.update(source_sha256=sha,crop_id=crop_identity('multiview',d['crop']),pixel=[o['pixel'][0]*3840/256,o['pixel'][1]*2160/256])
    transform=CalibrationTransform(cal);template=copy.deepcopy(cal['views']['side']['landmarks']['observations'][0])
    for i in range(16):
        name=f'cage_landmark_{i}';xyz=[-.8+i*.1,.45+(i%3)*.03,.8+(i%5)*.06];cage['landmarks'][name]=xyz
        for view in cal['views']:
            o=copy.deepcopy(template);o.update(id=f'obs_{name}_{view}',view=view,pixel=list(transform.world_to_pixel(view,*xyz)))
            cal['views'][view]['landmarks']['observations'].append(o)
            link=copy.deepcopy(cal['correspondences'][0]);link.update(id=f'link_{name}_{view}',observation_id=o['id'],world_entity_id=name)
            cal['correspondences'].append(link)
    curve=copy.deepcopy(cage['curves'][0])
    for i in range(8):
        c=copy.deepcopy(curve);c.update(id=f'preview_rail_{i}',points=[{'landmark':f'cage_landmark_{j}'} for j in range(i,i+5)],point_ids=[f'rail_{i}_point_{j}' for j in range(5)],handles='AUTO' if i%2 else 'VECTOR')
        cage['curves'].append(c)
    count=sum(len(d['landmarks']['observations']) for d in cal['views'].values())
    for i in range(5000-count):
        view=list(cal['views'])[i%4];o=copy.deepcopy(template)
        o.update(id=f'dense_{i}',view=view,pixel=[70+(i%100)*37,60+((i//100)%50)*40])
        cal['views'][view]['landmarks']['observations'].append(o)
    changes={'project.json':(json.dumps(project)+'\n').encode(),project['generated']['calibration']:(json.dumps(cal)+'\n').encode(),project['generated']['cage']:(json.dumps(cage)+'\n').encode()}
    commit(target,changes,expected_revision=w.revision,validator=w.validate)
print('Multiview fixtures prepared',flush=True)
