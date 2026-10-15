"""Rank-two affine calibration, including explicit anisotropic rectification."""
from ..core.errors import SchemaError
from ..core.project import finite

class CalibrationTransform:
    def __init__(self, config):
        finite(config)
        self.views = config['views']
        if set(self.views) != {'front','side','rear','top'}:
            raise SchemaError('Calibration requires front/side/rear/top')
        for view, data in self.views.items():
            for key in ('origin','u_basis','v_basis'):
                if len(data[key]) != 3:
                    raise SchemaError(f'{view}: invalid affine vector')
            u,v = data['u_basis'],data['v_basis']
            a,b,c = sum(x*x for x in u),sum(x*y for x,y in zip(u,v)),sum(x*x for x in v)
            if a*c-b*b <= 1e-24:
                raise SchemaError(f'{view}: singular calibration')

    def pixel_to_world(self, view, u, v):
        data = self.views[view]
        return tuple(o+a*u+b*v for o,a,b in zip(data['origin'],data['u_basis'],data['v_basis']))

    def world_to_pixel(self, view, x, y, z):
        data = self.views[view]
        q = [n-o for n,o in zip((x,y,z),data['origin'])]
        u,v = data['u_basis'],data['v_basis']
        a,b,c = sum(n*n for n in u),sum(n*m for n,m in zip(u,v)),sum(n*n for n in v)
        d,e = sum(n*m for n,m in zip(q,u)),sum(n*m for n,m in zip(q,v))
        det = a*c-b*b
        return ((d*c-e*b)/det,(e*a-d*b)/det)
