from .transforms import CalibrationTransform
from .panels import png_size
from ..core.errors import ReferenceError
from ..core.manifest import digest_file

def load(project):
    config = project.generated('calibration')
    return check_config(project,config)


def check_config(project, config):
    """Check calibration mathematics on an already schema-validated snapshot."""
    transform = CalibrationTransform(config)
    source = project.path(config['source'], exists=True)
    if png_size(source) != config['source_size'] or digest_file(source) != config['source_sha256']:
        raise ReferenceError('Calibration source image hash or dimensions changed')
    width,height = config['source_size']
    for view,data in config['views'].items():
        l,t,r,b = data['crop']
        if not (0 <= l < r <= width and 0 <= t < b <= height):
            raise ReferenceError(f'{view}: crop outside source image')
        if 'body_bbox' not in data['landmarks']:
            raise ReferenceError(f'{view}: envelope landmarks missing')
        left,top,right,bottom=data['landmarks']['body_bbox']
        a=transform.pixel_to_world(view,left,top);b=transform.pixel_to_world(view,right,bottom)
        axes={'side':[(0,'length_m'),(2,'height_m')],'top':[(0,'length_m'),(1,'width_m')],
              'front':[(1,'width_m'),(2,'height_m')],'rear':[(1,'width_m'),(2,'height_m')]}
        for axis,dimension in axes[view]:
            if abs(abs(b[axis]-a[axis])-project.data['dimensions'][dimension])>1e-6:
                raise ReferenceError(f'{view}: {dimension} disagrees with calibrated envelope')
    axles=config['wheel_geometry']['axles']
    if len(axles)>=2:
        wheelbase=max(a['x'] for a in axles)-min(a['x'] for a in axles)
        if abs(wheelbase-project.data['dimensions']['wheelbase_m'])>1e-6:
            raise ReferenceError('Wheelbase disagrees with shared axle landmarks')
    return config,transform
