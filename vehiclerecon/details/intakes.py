from ..core.errors import SchemaError

def validate_selection(selection):
    if set(selection)!={'u','v'}:raise SchemaError('UV selection needs both axes')
    for interval in selection.values():
        if len(interval)!=2:raise SchemaError('UV interval needs two bounds')
        lower,upper=interval
        if lower is not None and upper is not None and lower>=upper:
            raise SchemaError('Invalid UV interval')
    return selection
