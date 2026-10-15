from .curves import mirrored

def full_section(half,axis=1):
    """Match winding across the centerline without repeating the first point."""
    return mirrored(half[1:],axis,reverse=True)+list(map(tuple,half))
