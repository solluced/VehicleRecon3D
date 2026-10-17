"""Private browser fixtures; protected projects are read only inputs."""
import json,shutil,sys
from pathlib import Path
from vehiclerecon.core.project import REPOSITORY
sys.path.insert(0,str(REPOSITORY/'tests'))
from reconciliation_fixture import prepare
root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
request=prepare(root/'positive')
(root.parent/'positive-request.json').write_text(json.dumps(request),encoding='utf-8')
source=REPOSITORY/'projects/mark2';target=root/'mark2';target.mkdir()
project=json.loads((source/'project.json').read_text())
paths=['project.json',*project['references'].values(),*project['generated'].values(),
    'validation/rectification_candidate.json','validation/rectification_magnitude.json']
for name in paths:
    path=source/name;dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
print('Reconciliation fixtures prepared')
