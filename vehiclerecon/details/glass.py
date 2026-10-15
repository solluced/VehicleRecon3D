from ..core.errors import SchemaError

def validate_polygon(points,faces):
    if len(points)<3 or any(len(face)<3 or any(i<0 or i>=len(points) for i in face) for face in faces):
        raise SchemaError('Invalid glazing/pillar polygon')
    return points,faces
