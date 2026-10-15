import copy
import pytest
from vehiclerecon.core.project import Project,REPOSITORY,validate
from vehiclerecon.core.errors import SchemaError
from vehiclerecon.details.builder import check
from vehiclerecon.details.lights import selected,attachment_pairs
from vehiclerecon.details.intakes import validate_selection
from vehiclerecon.details.doors import panel_gap,backing
from vehiclerecon.details.wheels import revolved,radial_spokes
from vehiclerecon.details.wheel_arches import liner
from vehiclerecon.details.glass import validate_polygon
from vehiclerecon.details.mirrors import reflected
from vehiclerecon.details.bumpers import fins
from vehiclerecon.details.interior import validate_mass

def test_selection_strict_bounds():
    s={'u':[.1,.5],'v':[None,.8]}
    assert selected(.2,.5,s) and not selected(.1,.5,s) and not selected(.5,.5,s)
    assert not selected(.2,.8,s)
    with pytest.raises(SchemaError):validate_selection({'u':[.5,.1],'v':[0,1]})

def test_panel_gap_and_backing():
    points=[(0,1,0),(2,1,0)]
    for actual,expected in zip(panel_gap(points,.2),[(.1,1,0),(1.9,1,0)]):
        assert actual==pytest.approx(expected)
    assert backing(points,.1)==[(0,.9,0),(2,.9,0)]
    with pytest.raises(SchemaError):panel_gap(points,3)

def test_wheel_topology_and_spokes():
    vertices,faces=revolved([(1,-.1),(1,.1),(.8,.1),(.8,-.1)],8)
    assert len(vertices)==32 and len(faces)==32
    assert all(len(f)==4 for f in faces)
    assert len(radial_spokes([(1,0),(2,0),(2,.1)],7,.1,-1))==7
    with pytest.raises(SchemaError):revolved([],1)

def test_liner():
    vertices,faces=liner({'x':0,'z':1},{'segments':8,'depth':.5,'center_height':0,'radius':1,'start_angle':0,'span':180})
    assert len(vertices)==10 and len(faces)==8

def test_attachment():
    assert attachment_pairs({'sources':['a','b'],'offsets':[.1,.2]})==[('a',.1),('b',.2)]
    with pytest.raises(SchemaError):attachment_pairs({'sources':['a'],'offsets':[]})

def test_component_primitives():
    assert reflected([(1,2,3)])==[(1,-2,3)]
    assert fins([-.5,.5],(1,0,2))==[(1,-.5,2),(1,.5,2)]
    assert validate_polygon([(0,0,0),(1,0,0),(0,1,0)],[(0,1,2)])
    with pytest.raises(SchemaError):validate_polygon([(0,0,0)],[(0,1,2)])
    with pytest.raises(SchemaError):validate_mass({'size':[1,0,1]})

def test_details_schema_and_bounded_ops():
    data=Project(REPOSITORY/'projects/tesla').generated('details')
    assert len(check(data))==54
    bad=copy.deepcopy(data);bad['components'][0]['parameters']['operation']='eval'
    with pytest.raises(SchemaError):validate(bad,'details')
    bad=copy.deepcopy(data);bad['components'].append(bad['components'][0])
    with pytest.raises(SchemaError):check(bad)
