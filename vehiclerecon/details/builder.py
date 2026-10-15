from ..core.errors import SchemaError
from ..core.project import finite
from .intakes import validate_selection
from .interior import validate_mass
from .glass import validate_polygon
from .lights import attachment_pairs

OPERATIONS={'cavity','split','door_split','box','curve','polygon','wheels','torus','assembly','attach'}

def check(config):
    finite(config)
    ids=[r['id'] for r in config['components']]
    if len(set(ids))!=len(ids):raise SchemaError('Duplicate detail ID')
    for record in config['components']:
        p=record['parameters'];op=p['operation']
        if op not in OPERATIONS:raise SchemaError(f'Unsupported detail operation {op}')
        if op=='cavity':validate_selection(p['selection'])
        if op=='box':validate_mass(p)
        if op=='polygon':validate_polygon(p['points'],p['faces'])
        if op=='attach':attachment_pairs(p)
    return config['components']
