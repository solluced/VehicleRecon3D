"""Independent manual-source and 4K/5000-control performance test data."""
import copy
import json
import shutil
import sys
from pathlib import Path
from PIL import Image, ImageDraw
from vehiclerecon.core.project import REPOSITORY
from vehiclerecon.core.transactions import commit, atomic_write
from vehiclerecon.authoring.versions import create_draft
from vehiclerecon.authoring.service import AuthoringSession
from vehiclerecon.authoring.imports import import_reference
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.authoring.contracts import crop_identity

root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
if not (root/'analytic').exists():shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',root/'analytic')
image=Image.new('RGB',(3840,2160),'#dce5e7');draw=ImageDraw.Draw(image)
for x in range(0,3840,120):draw.line((x,0,x,2160),fill='#b9c9cf',width=2)
for y in range(0,2160,120):draw.line((0,y,3840,y),fill='#b9c9cf',width=2)
draw.rectangle((300,450,3500,1700),outline='#597984',width=12)
image.save(root.parent/'reference4k.png')
if '--performance' in sys.argv and not (root/'performance').exists():
    path=root/'performance';create_draft(path);session=AuthoringSession(path)
    import_reference(session,(root.parent/'reference4k.png').read_bytes(),expected_revision=session.revision)
    w=Workspace(path);cal=w.documents['calibration'];reference=w.documents['project']['references']['multiview']
    import hashlib
    sha=hashlib.sha256((path/reference).read_bytes()).hexdigest()
    cal['views']['side']['landmarks']['observations']=[{'id':f'perf_{i}','view':'side','kind':'point','semantic_role':'roof',
        'pixel':[60+(i%100)*37,60+(i//100)*40],'reference_id':'multiview','source_sha256':sha,
        'crop_id':crop_identity('multiview',cal['views']['side']['crop']),'revision':1,'provenance':{'type':'measured','method':'Analytical stress fixture'},
        'uncertainty_px':1,'visibility':'observed','measured':True} for i in range(5000)]
    changes={w.documents['project']['generated']['calibration']:(json.dumps(cal)+'\n').encode()}
    commit(path,changes,expected_revision=w.revision,validator=w.validate)
    layers={'image':{'name':'Source Image','category':'image','visible':True,'locked':True,'opacity':1}}
    for i,key in enumerate(['observations','curves','datums']+[f'layer_{i}' for i in range(16)]):
        layers[key]={'name':key,'category':'observations','visible':True,'locked':False,'opacity':1}
    assignments={f'perf_{i}':list(layers)[1+i%19] for i in range(5000)}
    atomic_write(path,'.studio/session.json',json.dumps({'active_view':'side','layers':layers,'assignments':assignments}).encode())
print('Browser fixtures prepared',flush=True)
