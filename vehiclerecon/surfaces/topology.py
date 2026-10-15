"""Topology policy helpers, without Blender imports or implicit mutation."""
from ..core.errors import SchemaError

def valid_schedule(values):
    if len(values)<2 or values[0]!=0 or values[-1]!=1 or any(a>=b for a,b in zip(values,values[1:])):
        raise SchemaError('Patch schedule must increase strictly from 0 to 1')
    return values
