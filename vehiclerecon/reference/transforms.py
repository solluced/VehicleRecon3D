"""Affine plane calibration with optional invertible source-axis rectification."""
from ..core.errors import SchemaError
from ..core.project import finite
from .rectification import AxisRectification

class CalibrationTransform:
    def __init__(self, config):
        finite(config)
        self.views = config['views']
        self.rectifications = {}
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
            if 'rectification' in data:
                self.rectifications[view] = AxisRectification(data['rectification'])

    def pixel_to_world(self, view, u, v):
        data = self.views[view]
        if view in self.rectifications:
            warp = self.rectifications[view]
            if warp.axis == 0:
                u = warp.forward(u)
            else:
                v = warp.forward(v)
        return tuple(o+a*u+b*v for o,a,b in zip(data['origin'],data['u_basis'],data['v_basis']))

    def world_to_pixel(self, view, x, y, z):
        data = self.views[view]
        q = [n-o for n,o in zip((x,y,z),data['origin'])]
        u,v = data['u_basis'],data['v_basis']
        a,b,c = sum(n*n for n in u),sum(n*m for n,m in zip(u,v)),sum(n*n for n in v)
        d,e = sum(n*m for n,m in zip(q,u)),sum(n*m for n,m in zip(q,v))
        det = a*c-b*b
        result = [(d*c-e*b)/det,(e*a-d*b)/det]
        if view in self.rectifications:
            warp = self.rectifications[view]
            result[warp.axis] = warp.inverse(result[warp.axis])
        return tuple(result)

    def pixel_polyline_to_world(self, view, points, *, closed=False, max_step_px=1.):
        """Densify only nonlinear projected edges; preserve the affine path."""
        import math
        points = list(points)
        if view not in self.rectifications:
            return [self.pixel_to_world(view, *point) for point in points]
        if not math.isfinite(max_step_px) or max_step_px <= 0:
            raise SchemaError('Projected polyline step must be positive')
        if not points:
            return []
        axis = self.rectifications[view].axis
        result = []
        edges = list(zip(points, points[1:]+points[:1] if closed else points[1:]))
        for a, b in edges:
            count = max(1, math.ceil(abs(b[axis]-a[axis])/max_step_px))
            for i in range(count):
                t = i/count
                result.append(self.pixel_to_world(view, *[x+(y-x)*t for x, y in zip(a, b)]))
        if not closed:
            result.append(self.pixel_to_world(view, *points[-1]))
        return result


def reference_grid(transform, view, max_step_px=1.):
    """Texture grid for nonlinear references; original pixels remain the UVs.

    Each strip spans at most one source pixel on the nonlinear axis. The other
    axis remains affine, so it needs no interior vertices. No warped pixel file
    or independent per-view vehicle mesh is produced.
    """
    import math
    if not math.isfinite(max_step_px) or max_step_px <= 0:
        raise SchemaError('Reference grid step must be positive')
    data = transform.views[view]
    l, t, r, b = data['crop']
    warp = transform.rectifications[view]
    start, end = (l, r) if warp.axis == 0 else (t, b)
    count = max(1, math.ceil((end-start)/max_step_px))
    samples = [start+(end-start)*i/count for i in range(count+1)]
    pixels = []
    for value in samples:
        pixels.extend([(value, b), (value, t)] if warp.axis == 0 else [(l, value), (r, value)])
    vertices = [[a+d for a, d in zip(transform.pixel_to_world(view, u, v), data['plane_offset'])]
                for u, v in pixels]
    faces = [(2*i, 2*i+2, 2*i+3, 2*i+1) for i in range(count)]
    uv = [((u-l)/(r-l), (b-v)/(b-t)) for u, v in pixels]
    return vertices, faces, uv
