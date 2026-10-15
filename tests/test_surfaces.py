import pytest
from vehiclerecon.core.errors import SchemaError,ReferenceError
from vehiclerecon.surfaces.curves import Vector,polyline,chord_hermite,shape_preserving_hermite,cubic,at_x,bezier_rail_range
from vehiclerecon.surfaces.coons import coons,bilinear_patch
from vehiclerecon.surfaces.patches import cubic_boundary_roll,ribbon,arch_annulus,boundary_stitch,grid,parameters
from vehiclerecon.surfaces.builder import Graph,order,OPERATIONS
from vehiclerecon.surfaces.topology import valid_schedule

P=[(0,0,0),(1,0,0),(2,0,0)]
@pytest.mark.parametrize('operation',[polyline,chord_hermite,shape_preserving_hermite])
def test_curves(operation):
    f=operation(P)
    assert f(0)==P[0] and f(1)==P[-1]
    assert f(.5)==pytest.approx((1,0,0))

def test_degenerate_hermite():
    with pytest.raises(SchemaError):chord_hermite([(0,0,0),(0,0,0)])

def test_bezier():
    pts=[{'co':Vector(p),'left':Vector(p),'right':Vector(p)} for p in P]
    assert at_x(pts,1).x==pytest.approx(1,abs=1e-7)
    assert bezier_rail_range(pts,0,2)(.5).x==pytest.approx(1,abs=1e-7)
    assert at_x(pts,-1)==P[0] and at_x(pts,3)==P[-1]
    with pytest.raises(SchemaError):at_x(pts[::-1],1)

def test_coons():
    bottom=polyline([(0,0,0),(1,0,0)]);top=polyline([(0,1,0),(1,1,0)])
    f=coons(bottom,top)
    assert f(.3,.7)==pytest.approx((.3,.7,0))
    with pytest.raises(SchemaError):coons(bottom,top,polyline([(5,0,0),(5,1,0)]))
    assert bilinear_patch([(0,0,0),(1,0,0),(1,1,0),(0,1,0)])(.3,.7)==pytest.approx((.3,.7,0))

def test_roll_ribbon_annulus():
    inner=polyline([(0,0,0),(1,0,0)]);outer=polyline([(0,1,1),(1,1,1)])
    f=cubic_boundary_roll(inner,outer,[.5,0,.75],.65,[.1])
    assert f(.2,0)==inner(.2) and f(.2,1)==outer(.2)
    assert ribbon(inner,[0,0,0],[0,1,1])(.2,.4)==pytest.approx((.2,.4,.4))
    a=arch_annulus([(0,0,0),(1,0,0)],[(0,1,1),(1,1,1)],[.5,0,.75],.65,[0,.2])
    assert a(0,0)==(0,0,0) and a(1,1)==(1,1,1)

def test_stitch():
    vertices,faces=boundary_stitch([Vector((0,0,0)),Vector((1,0,0))],[Vector((0,1,0)),Vector((1,1,0))],[.5,1])
    assert len(vertices)==6 and len(faces)==2
    with pytest.raises(SchemaError):boundary_stitch([],[],[1])

def test_schedules():
    assert valid_schedule(parameters(4,[.012,.988]))
    with pytest.raises(SchemaError):valid_schedule([0,.5,.4,1])

def node(id,op,parameters,deps=()):return {'id':id,'op':op,'parameters':parameters,'dependencies':list(deps)}

def test_order_errors():
    with pytest.raises(ReferenceError):order([node('a','offset',{},['missing'])])
    with pytest.raises(SchemaError):order([node('a','offset',{},['b']),node('b','offset',{},['a'])])
    with pytest.raises(SchemaError):order([node('a','offset',{}),node('a','offset',{})])

def test_graph_point_and_offset_operations():
    nodes=[node('curve','polyline',{'points':P}),node('point','curve_sample',{'curve':'curve','t':.5},['curve']),node('offset','offset',{'source':'point','offset':[0,1,0]},['point']),node('blend','lerp',{'a':'point','b':'offset','t':.5},['point','offset'])]
    g=Graph({'nodes':nodes,'patches':[]})
    assert g.get('blend')==pytest.approx((1,.5,0))
    with pytest.raises(ReferenceError):g.get('missing')
    with pytest.raises(SchemaError):Graph({'nodes':[node('bad','eval',{})]})

def test_full_graph_uses_only_bounded_operations():
    from vehiclerecon.core.project import Project,REPOSITORY
    p=Project(REPOSITORY/'projects/tesla');data=p.generated('surface_graph')
    assert all(n['op'] in OPERATIONS for n in data['nodes'])
    assert len(order(data['nodes']))==len(data['nodes'])
