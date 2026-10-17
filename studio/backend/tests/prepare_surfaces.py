"""Private browser/performance projects; never writes accepted vehicle fixtures."""
import json
import shutil
import sys
from pathlib import Path
from vehiclerecon.core.project import REPOSITORY
from vehiclerecon.core.transactions import commit
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.authoring.service import AuthoringSession


def prepare(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    for name in ('surfaces','rejected','dense'):
        target=root/name
        if target.exists():continue
        shutil.copytree(REPOSITORY/'tests/fixtures/surface_authoring_v2',target,
                        ignore=shutil.ignore_patterns('.cache','output'))
        w=Workspace(target);data=w.documents['project'];data['asset_name']={'surfaces':'Surface_Study','rejected':'Rejected_Surface_Study','dense':'Dense_Surface_Study'}[name]
        graph=w.documents['surface_graph']
        if name=='dense':
            for i in range(25):
                node={'id':f'grid.sample.{i}','op':'bilinear_patch','parameters':{'points':[[i%5*1.2,i//5*1.2,0],[i%5*1.2+1,i//5*1.2,0],[i%5*1.2+1,i//5*1.2+1,0],[i%5*1.2,i//5*1.2+1,0]]},'dependencies':[],'draft':False,'reversed':[]}
                graph['nodes'].append(node);graph['patches'].append({'id':f'grid.panel.{i}','sample':node['id'],'name':f'Grid panel {i}','semantic_role':'panel','resolution':[16,16],'material':'SURFACE','collection':'02_SURFACES','settings':{}})
        changes={'project.json':(json.dumps(data,indent=2)+'\n').encode(),data['generated']['surface_graph']:(json.dumps(graph,indent=2)+'\n').encode()}
        commit(target,changes,expected_revision=w.revision,validator=w.validate)
        if name=='rejected':
            session=AuthoringSession(target);session.apply([dict(type='SetSourceDisposition',decision='INCONSISTENT_SOURCE',reviewer='Fixture author',notes=['Explicit synthetic source conflict.'])],expected_revision=session.revision)
    target=root/'mark2_readonly'
    if not target.exists():
        target.mkdir();source=REPOSITORY/'projects/mark2'
        shutil.copy2(source/'project.json',target/'project.json')
        for folder in ('input','generated'):shutil.copytree(source/folder,target/folder)
        from vehiclerecon.core.manifest import digest_file
        baseline={p.relative_to(target).as_posix():digest_file(p) for p in target.rglob('*') if p.is_file()}
        (root.parent/'mark2-surface-baseline.json').write_text(json.dumps(baseline),encoding='utf-8')


if __name__=='__main__':
    if len(sys.argv)>2 and sys.argv[2]=='--check-mark2':
        from vehiclerecon.core.manifest import digest_file
        root=Path(sys.argv[1]);baseline=json.loads((root.parent/'mark2-surface-baseline.json').read_text(encoding='utf-8'))
        if not all(digest_file(root/'mark2_readonly'/path)==sha for path,sha in baseline.items()):raise RuntimeError('Mark II bytes changed')
        print('Mark II canonical hashes PASS')
    elif len(sys.argv)>2 and sys.argv[2] in ('--edit-cage','--accept-cage'):
        from vehiclerecon.core.errors import LockError
        import time
        for attempt in range(40):
            try:
                path=Path(sys.argv[1])/'surfaces';session=AuthoringSession(path)
                if sys.argv[2]=='--edit-cage':command=dict(type='MoveWorldLandmark',world_entity_id='roof_corner',point=[.0001,.5,1])
                else:
                    from vehiclerecon.authoring.reviews import subject
                    command=dict(type='SetCageReview',decision='ACCEPTED',reviewer='Analytical E2E inspector',notes=['Inspected current analytical residuals after sub-tolerance synthetic edit.'],expected_subject=subject(Workspace(path),'cage'))
                session.apply([command],expected_revision=session.revision)
                break
            except LockError:
                if attempt==39:raise
                time.sleep(.05)
    else:prepare(sys.argv[1])
