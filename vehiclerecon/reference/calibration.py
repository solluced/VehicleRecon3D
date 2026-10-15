from .transforms import CalibrationTransform
from .panels import png_size
from ..core.errors import ReferenceError
from ..core.manifest import digest_file

def load(project):
    config = project.generated('calibration')
    transform = CalibrationTransform(config)
    source = project.path(config['source'], exists=True)
    if png_size(source) != config['source_size'] or digest_file(source) != config['source_sha256']:
        raise ReferenceError('Calibration source image hash or dimensions changed')
    width,height = config['source_size']
    for view,data in config['views'].items():
        l,t,r,b = data['crop']
        if not (0 <= l < r <= width and 0 <= t < b <= height):
            raise ReferenceError(f'{view}: crop outside source image')
    return config,transform
