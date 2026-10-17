"""Private browser fixtures for actual provider/UI workflows and 4K timing."""
import copy,json,shutil,sys
from pathlib import Path
from PIL import Image,ImageDraw
from vehiclerecon.core.project import REPOSITORY
from vehiclerecon.core.manifest import digest_file
from vehiclerecon.authoring.contracts import crop_identity
from vehiclerecon.authoring.workspace import Workspace

def prepare(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    names=['strong_edge','body_mask','circle_wheels','curved_contour','weak_noisy','false_positive','performance']
    for name in names:
        target=root/('cv_'+name);shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',target)
        if name=='performance':
            image=Image.new('RGB',(3840,2160),'#f4f5f6');draw=ImageDraw.Draw(image)
            draw.line((500,350,500,1750),fill='#111111',width=6)
            draw.polygon([(1250,1450),(1300,1100),(1700,1050),(1900,700),(2500,700),(2800,1050),(3200,1180),(3250,1450)],fill='#354e65')
            for x in (1600,2900):draw.ellipse((x-150,1300,x+150,1600),fill='#16242e')
            size=[3840,2160]
        else:
            image=Image.open(REPOSITORY/f'tests/fixtures/cv/{name}.png').copy();size=[256,256]
            if name=='body_mask':ImageDraw.Draw(image).rectangle((24,50,47,73),fill='#345068')
        image.save(target/'input/reference.png');sha=digest_file(target/'input/reference.png')
        project=json.loads((target/'project.json').read_text());project.update(asset_name='cv_'+name,project_id='cv_'+name)
        cal=json.loads((target/'generated/calibration.json').read_text());cal.update(source_size=size,source_sha256=sha)
        for view,d in cal['views'].items():
            d['crop']=[16,16,240,240] if name!='performance' and view=='side' else [0,0,*size]
            if name=='performance':
                d['u_basis']=[v*256/size[0] for v in d['u_basis']];d['v_basis']=[v*256/size[1] for v in d['v_basis']]
                d['landmarks']['body_bbox']=[v*(size[0]/256 if i%2==0 else size[1]/256) for i,v in enumerate(d['landmarks']['body_bbox'])]
                d['camera']['size']=size
            for o in d['landmarks']['observations']:
                o.update(source_sha256=sha,crop_id=crop_identity('multiview',d['crop']))
                if name=='performance':o['pixel']=[o['pixel'][0]*size[0]/256,o['pixel'][1]*size[1]/256]
        (target/'project.json').write_text(json.dumps(project,indent=2)+'\n',encoding='utf-8')
        (target/'generated/calibration.json').write_text(json.dumps(cal,indent=2)+'\n',encoding='utf-8')
        Workspace(target)
    print('CV browser fixtures prepared',flush=True)

if __name__=='__main__':prepare(sys.argv[1])
