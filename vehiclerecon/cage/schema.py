from ..core.project import finite
from ..core.errors import SchemaError
from .curves import expand

def check(config,geometry):
    finite(config)
    records=expand(config,geometry)
    for record in records:
        if len(record['points'])<2 or any(len(p)!=3 for p in record['points']):
            raise SchemaError(f"Invalid cage cardinality: {record['id']}")
        if record['cyclic'] and len(record['points'])<3:
            raise SchemaError('Cyclic guide needs at least three points')
    return records
