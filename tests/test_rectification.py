import copy
import math
import pytest

from vehiclerecon.core.errors import ReferenceError, SchemaError
from vehiclerecon.core.project import Project, REPOSITORY, validate
from vehiclerecon.reference.rectification import PiecewiseMonotonicAxisWarp, AxisRectification
from vehiclerecon.reference.transforms import CalibrationTransform, reference_grid


def config(axis='u'):
    return {'type': 'piecewise_monotonic', 'axis': axis,
            'image_domain_px': [100, 900], 'affine_domain_px': [120, 920],
            'anchors': [{'image': x, 'world_normalized': y, 'semantic': name}
                        for x, y, name in [(0, 0, 'datum_start'), (.3, .31, 'feature_a'),
                                           (.65, .64, 'feature_b'), (1, 1, 'datum_end')]]}


@pytest.mark.parametrize('anchors', [[0, 1], [-.2, 0, .3, .7, 1, 1.3]])
def test_identity(anchors):
    warp = PiecewiseMonotonicAxisWarp(anchors, anchors)
    for x in [-2, -.2, 0, .15, .7, 1, 2]:
        assert warp(x) == pytest.approx(x, abs=1e-14)
        assert warp.inverse(x) == pytest.approx(x, abs=1e-14)
        assert warp.derivative(x) == pytest.approx(1, abs=1e-14)
    assert warp.maximum_identity_correction()['maximum_absolute_normalized'] < 1e-14


def test_two_anchor_affine_equivalent():
    warp = PiecewiseMonotonicAxisWarp([-2, 3], [10, 20])
    for x in [-5, -2, 0, 2, 3, 8]:
        assert warp(x) == pytest.approx(2*x+14)
        assert warp.inverse(2*x+14) == pytest.approx(x)
        assert warp.derivative(x) == pytest.approx(2)


def test_anchor_exactness_monotonicity_inverse_and_c1():
    source = [0, .3, .65, 1]
    target = [0, .31, .64, 1]
    warp = PiecewiseMonotonicAxisWarp(source, target)
    for x, y in zip(source, target):
        assert warp(x) == pytest.approx(y, abs=1e-15)
        assert warp.inverse(y) == pytest.approx(x, abs=1e-15)
        assert warp.derivative(x-1e-8) == pytest.approx(warp.derivative(x+1e-8), abs=1e-7)
    values = [-.5+i/1000 for i in range(2001)]
    assert all(warp(a) < warp(b) for a, b in zip(values, values[1:]))
    minimum, maximum = warp.derivative_range()
    for x in values:
        assert minimum-1e-12 <= warp.derivative(x) <= maximum+1e-12
        assert warp.derivative(x) > 0
        assert warp.inverse(warp(x)) == pytest.approx(x, abs=1e-13)
    peak = warp.maximum_identity_correction()
    assert peak['maximum_absolute_normalized'] >= max(abs(warp(x)-x) for x in values if 0 <= x <= 1)-1e-14
    assert warp.derivative(peak['source_normalized']) == pytest.approx(1, abs=1e-12)


@pytest.mark.parametrize('source,target', [
    ([0], [0]), ([0, 1], [0]), ([0, .5, .5, 1], [0, .3, .7, 1]),
    ([0, .7, .3, 1], [0, .3, .7, 1]), ([0, .5, 1], [0, -.1, 1]),
    ([0, .5, 1], [0, 1, 1]), ([0, 1], [0, math.inf]),
    ([0, math.nan, 1], [0, .5, 1]), ([False, 1], [0, 1]),
    # A monotone data set whose standard PCHIP endpoint derivative is zero.
    ([0, .5, 1], [0, .01, 1]),
])
def test_invalid_or_noninvertible_data_rejected(source, target):
    with pytest.raises(SchemaError):
        PiecewiseMonotonicAxisWarp(source, target)


def test_excessive_warp_is_not_accepted():
    data = config()
    data['anchors'][1]['world_normalized'] = .4
    with pytest.raises(ReferenceError, match='local scale'):
        AxisRectification(data)


@pytest.mark.parametrize('change', ['missing_anchor', 'reversed_domain', 'bad_axis', 'bad_limit'])
def test_invalid_rectification_contract(change):
    data = config()
    if change == 'missing_anchor':
        data['anchors'][0]['world_normalized'] = .001
    if change == 'reversed_domain':
        data['image_domain_px'].reverse()
    if change == 'bad_axis':
        data['axis'] = 'x'
    if change == 'bad_limit':
        data['max_scale_change'] = -1
    with pytest.raises(SchemaError):
        AxisRectification(data)


@pytest.mark.parametrize('axis', ['u', 'v'])
def test_pixel_world_pixel_and_source_grid(axis):
    project = Project(REPOSITORY/'projects/tesla')
    data = copy.deepcopy(project.generated('calibration'))
    data['views']['top']['rectification'] = config(axis)
    validate(data, 'calibration')
    transform = CalibrationTransform(data)
    for point in [(-100, -100), (100, 120), (340.2, 599.7), (900, 900), (2000, 1800)]:
        world = transform.pixel_to_world('top', *point)
        assert transform.world_to_pixel('top', *world) == pytest.approx(point, abs=1e-9)
    vertices, faces, uv = reference_grid(transform, 'top')
    assert len(vertices) > 4 and len(faces) > 1
    l, t, r, b = data['views']['top']['crop']
    offset = data['views']['top']['plane_offset']
    for vertex, (s, q) in zip(vertices, uv):
        pixel = (l+s*(r-l), b-q*(b-t))
        assert vertex == pytest.approx([x+d for x, d in zip(transform.pixel_to_world('top', *pixel), offset)])


def test_tesla_identity_warp_preserves_affine_projection():
    data = Project(REPOSITORY/'projects/tesla').generated('calibration')
    original = CalibrationTransform(data)
    identity = copy.deepcopy(data)
    for view in identity['views'].values():
        view['rectification'] = {'type': 'piecewise_monotonic', 'axis': 'u',
                                'image_domain_px': [0, 1], 'affine_domain_px': [0, 1],
                                'anchors': [{'image': v, 'world_normalized': v, 'semantic': str(v)} for v in (0, 1)]}
    transformed = CalibrationTransform(identity)
    for view in data['views']:
        for point in [(0, 0), (500.3, 700.8), (1536, 1152)]:
            assert transformed.pixel_to_world(view, *point) == original.pixel_to_world(view, *point)
            world = original.pixel_to_world(view, *point)
            assert transformed.world_to_pixel(view, *world) == original.world_to_pixel(view, *world)


def test_rectification_schema_rejects_unknown_properties():
    data = Project(REPOSITORY/'projects/tesla').generated('calibration')
    data['views']['side']['rectification'] = config()
    data['views']['side']['rectification']['code'] = 'not executable'
    with pytest.raises(SchemaError):
        validate(data, 'calibration')


def test_closed_trace_subdivision_preserves_vertices_and_roundtrips():
    data = Project(REPOSITORY/'projects/tesla').generated('calibration')
    data['views']['top']['rectification'] = config()
    transform = CalibrationTransform(data)
    points = [(100, 200), (500, 300), (900, 200)]
    dense = transform.pixel_polyline_to_world('top', points, closed=True)
    assert len(dense) == 1600
    pixels = [transform.world_to_pixel('top', *p) for p in dense]
    for point in points:
        assert any(max(abs(a-b) for a, b in zip(point, p)) < 1e-9 for p in pixels)
    assert all(abs(a[0]-b[0]) <= 1+1e-9 for a, b in zip(pixels, pixels[1:]+pixels[:1]))


@pytest.mark.blender
def test_nonlinear_reference_build_has_real_texture_grid(tmp_path):
    import json
    import shutil
    import subprocess
    from vehiclerecon.core.manifest import write_json
    from vehiclerecon.blender.runner import run, discover
    from vehiclerecon.reference.calibration import load
    source = REPOSITORY/'projects/tesla'
    shutil.copyfile(source/'project.json', tmp_path/'project.json')
    for folder in ('input', 'generated'):
        shutil.copytree(source/folder, tmp_path/folder)
    project = Project(tmp_path)
    data = project.generated('calibration')
    left, _, right, _ = data['views']['top']['landmarks']['body_bbox']
    rect = config()
    rect['image_domain_px'] = rect['affine_domain_px'] = [left, right]
    data['views']['top']['rectification'] = rect
    write_json(project.path(project.data['generated']['calibration']), data)
    load(project)
    run(project, 'calibration')
    report = project.path('.cache/texture_grid_inspection.json')
    expr = ("import bpy,json; from pathlib import Path; "
            "o=bpy.data.objects['REF_TOP']; "
            f"Path({str(report)!r}).write_text(json.dumps({{'vertices':[list(v.co) for v in o.data.vertices],"
            "'faces':len(o.data.polygons),'uvs':[list(x.uv) for x in o.data.uv_layers.active.data],"
            "'indices':[x.vertex_index for x in o.data.loops]}))")
    result = subprocess.run([str(discover()), '--background', str(project.path('.cache/calibration.blend')),
                             '--python-exit-code', '1', '--python-expr', expr],
                            capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout+result.stderr
    actual = json.loads(report.read_text())
    expected, faces, uv = reference_grid(CalibrationTransform(data), 'top')
    assert actual['faces'] == len(faces) and actual['faces'] > 1
    assert len(actual['vertices']) == len(expected)
    for a, b in zip(actual['vertices'], expected):
        assert a == pytest.approx(b, abs=1e-6)
    for a, index in zip(actual['uvs'], actual['indices']):
        assert a == pytest.approx(uv[index], abs=1e-7)
