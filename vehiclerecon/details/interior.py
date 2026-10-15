from ..core.errors import SchemaError

def validate_mass(config):
    if len(config['size'])!=3 or any(value<=0 for value in config['size']):
        raise SchemaError('Primitive mass dimensions must be positive')
    return config
