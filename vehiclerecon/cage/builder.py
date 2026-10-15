from .schema import check

def records(project,*,validate=True):
    config=project.generated('cage',check=validate)
    geometry=project.generated('calibration',check=validate)['wheel_geometry']
    return config,check(config,geometry)
