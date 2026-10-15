"""Declarative aperture selection and paired surface attachment policy."""
from ..core.errors import SchemaError

def selected(u,v,selection):
    for value,axis in ((u,'u'),(v,'v')):
        lower,upper=selection[axis]
        if lower is not None and value<=lower:return False
        if upper is not None and value>=upper:return False
    return True

def attachment_pairs(config):
    if len(config['sources'])!=len(config['offsets']) or not config['sources']:
        raise SchemaError('Attachment sources/offsets must match')
    return list(zip(config['sources'],config['offsets']))
