"""Invertible one-axis source rectification; no vehicle geometry is fitted here.

PCHIP uses the weighted harmonic-mean derivatives of Fritsch/Butland and
one-sided endpoint slopes. Outside the anchors we use positive linear tails,
not extrapolated cubics. See docs/reference_rectification.md.
"""
from bisect import bisect_right
import math

from ..core.errors import SchemaError, ReferenceError


def _numbers(values):
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
           not math.isfinite(v) for v in values):
        raise SchemaError('Rectification coordinates must be finite numbers')
    return tuple(float(v) for v in values)


class PiecewiseMonotonicAxisWarp:
    """Strictly increasing C1 cubic Hermite interpolation, with exact inverse."""

    def __init__(self, source, target):
        self.x, self.y = _numbers(source), _numbers(target)
        if len(self.x) != len(self.y) or len(self.x) < 2:
            raise SchemaError('Rectification needs at least two paired anchors')
        if any(b <= a for values in (self.x, self.y)
               for a, b in zip(values, values[1:])):
            raise SchemaError('Rectification source and target must be strictly increasing; no duplicates')
        h = [b-a for a, b in zip(self.x, self.x[1:])]
        d = [(b-a)/step for a, b, step in zip(self.y, self.y[1:], h)]
        if len(d) == 1:
            self.slopes = (d[0], d[0])
        else:
            def endpoint(h0, h1, d0, d1):
                value = ((2*h0+h1)*d0-h0*d1)/(h0+h1)
                return max(0., min(3*d0, value))
            slopes = [endpoint(h[0], h[1], d[0], d[1])]
            for i in range(1, len(self.x)-1):
                w1, w2 = 2*h[i]+h[i-1], h[i]+2*h[i-1]
                slopes.append((w1+w2)/(w1/d[i-1]+w2/d[i]))
            slopes.append(endpoint(h[-1], h[-2], d[-1], d[-2]))
            self.slopes = tuple(slopes)
        self.coefficients = []
        for i, step in enumerate(h):
            y0, y1 = self.y[i:i+2]
            m0, m1 = self.slopes[i:i+2]
            self.coefficients.append((2*(y0-y1)+step*(m0+m1),
                                      3*(y1-y0)-step*(2*m0+m1), step*m0, y0))
        if self.derivative_range()[0] <= 0:
            raise SchemaError('Rectification has a non-positive derivative; strict invertibility required')

    def _interval(self, value):
        return max(0, min(len(self.x)-2, bisect_right(self.x, value)-1))

    def __call__(self, value):
        value, = _numbers([value])
        if value <= self.x[0]:
            return self.y[0]+self.slopes[0]*(value-self.x[0])
        if value >= self.x[-1]:
            return self.y[-1]+self.slopes[-1]*(value-self.x[-1])
        i = self._interval(value)
        t = (value-self.x[i])/(self.x[i+1]-self.x[i])
        a, b, c, d = self.coefficients[i]
        return ((a*t+b)*t+c)*t+d

    def derivative(self, value):
        value, = _numbers([value])
        if value <= self.x[0]:
            return self.slopes[0]
        if value >= self.x[-1]:
            return self.slopes[-1]
        i = self._interval(value)
        h = self.x[i+1]-self.x[i]
        t = (value-self.x[i])/h
        a, b, c, _ = self.coefficients[i]
        return (3*a*t*t+2*b*t+c)/h

    def derivative_range(self):
        values = list(self.slopes)
        for i, (a, b, c, _) in enumerate(self.coefficients):
            if a:
                t = -b/(3*a)
                if 0 < t < 1:
                    values.append((3*a*t*t+2*b*t+c)/(self.x[i+1]-self.x[i]))
        return min(values), max(values)

    def inverse(self, value):
        value, = _numbers([value])
        if value <= self.y[0]:
            return self.x[0]+(value-self.y[0])/self.slopes[0]
        if value >= self.y[-1]:
            return self.x[-1]+(value-self.y[-1])/self.slopes[-1]
        i = bisect_right(self.y, value)-1
        if value == self.y[i]:
            return self.x[i]
        lo, hi = self.x[i:i+2]
        # Solve this interpolant, rather than interpolating swapped anchors.
        for _ in range(64):
            mid = (lo+hi)/2
            if self(mid) < value:
                lo = mid
            else:
                hi = mid
        return (lo+hi)/2

    def maximum_identity_correction(self, lower=None, upper=None):
        """Exact extrema of f(r)-r on the supplied interval, including tails."""
        lower = self.x[0] if lower is None else lower
        upper = self.x[-1] if upper is None else upper
        if not math.isfinite(lower) or not math.isfinite(upper) or lower > upper:
            raise SchemaError('Invalid rectification audit interval')
        candidates = [lower, upper, *[v for v in self.x if lower <= v <= upper]]
        for i, (a, b, c, _) in enumerate(self.coefficients):
            h = self.x[i+1]-self.x[i]
            qa, qb, qc = 3*a, 2*b, c-h
            roots = []
            if abs(qa) < 1e-15:
                if abs(qb) > 1e-15:
                    roots = [-qc/qb]
            elif qb*qb-4*qa*qc >= 0:
                disc = math.sqrt(qb*qb-4*qa*qc)
                roots = [(-qb-disc)/(2*qa), (-qb+disc)/(2*qa)]
            for t in roots:
                x = self.x[i]+t*h
                if 0 <= t <= 1 and lower <= x <= upper:
                    candidates.append(x)
        where = max(candidates, key=lambda x: abs(self(x)-x))
        return {'source_normalized': where, 'correction_normalized': self(where)-where,
                'maximum_absolute_normalized': abs(self(where)-where)}


class AxisRectification:
    """Normalize raw pixels, warp one axis, then restore affine-plane pixels."""

    def __init__(self, config):
        if config.get('type') != 'piecewise_monotonic' or config.get('axis') not in ('u', 'v'):
            raise SchemaError('Unsupported source rectification type or axis')
        self.axis = 0 if config['axis'] == 'u' else 1
        try:
            self.image_domain = _numbers(config['image_domain_px'])
            self.affine_domain = _numbers(config['affine_domain_px'])
            if any(len(v) != 2 or v[1] <= v[0] for v in (self.image_domain, self.affine_domain)):
                raise SchemaError('Rectification domains need two increasing pixel coordinates')
            anchors = config['anchors']
            self.warp = PiecewiseMonotonicAxisWarp([a['image'] for a in anchors],
                                                  [a['world_normalized'] for a in anchors])
        except (KeyError, TypeError) as exc:
            raise SchemaError('Incomplete rectification data') from exc
        if not all(any(x == endpoint and y == endpoint for x, y in zip(self.warp.x, self.warp.y))
                   for endpoint in (0, 1)):
            raise SchemaError('Rectification requires exact normalized 0/0 and 1/1 datum anchors')
        limit, = _numbers([config.get('max_scale_change', .1)])
        if not 0 <= limit < 1:
            raise SchemaError('Rectification max_scale_change must be in [0,1)')
        minimum, maximum = self.warp.derivative_range()
        if minimum < 1-limit-1e-12 or maximum > 1+limit+1e-12:
            raise ReferenceError(f'Rectification local scale {minimum:.6f}..{maximum:.6f} exceeds declared +/-{limit:.1%} limit')

    def forward(self, value):
        a, b = self.image_domain
        c, d = self.affine_domain
        return c+(d-c)*self.warp((value-a)/(b-a))

    def inverse(self, value):
        a, b = self.image_domain
        c, d = self.affine_domain
        return a+(b-a)*self.warp.inverse((value-c)/(d-c))
