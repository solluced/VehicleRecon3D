"""Create an authoring scaffold without guessing any vehicle geometry."""
from pathlib import Path
import re
from .errors import SchemaError
from .manifest import write_json
from .project import REPOSITORY

def initialize(root,profile='sedan'):
    root=Path(root).resolve()
    if not re.fullmatch('[a-z_]+',profile):raise SchemaError('Unsafe profile identifier')
    if not (REPOSITORY/'profiles'/f'{profile}.json').is_file():raise SchemaError('Unknown automobile profile')
    if (root/'project.json').exists():raise SchemaError('Project already exists; refusing to overwrite')
    for folder in ('input','generated','validation','output','.cache'):(root/folder).mkdir(parents=True,exist_ok=True)
    identity=re.sub('[^a-z0-9_]','_',root.name.lower())
    if not identity or not identity[0].isalpha():identity='vehicle_'+identity
    draft={'schema_version':1,'project_id':identity,'category':'automobile','vehicle_profile':profile,'asset_name':identity,
           'references':{'multiview':'input/multiview.png','control_overlay':'input/control_overlay.png','surface_target':'input/surface_target.png'},
           'dimensions':{'length_m':None,'width_m':None,'height_m':None,'wheelbase_m':None,'provenance':'UNMEASURED — calibration required'},
           'generated':{},'materials':[],'scene':{},'presentation':{},'export':{},'viewer':{},'validation':{}}
    write_json(root/'project.json',draft)
    return {'status':'PASS','state':'DRAFT_REQUIRES_AUTHORING','path':str(root),
            'next':'Add references and measured/authorized dimensions; author calibration, semantic cage, surface graph and detail data. inspect/run reject this incomplete draft.'}
