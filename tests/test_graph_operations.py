"""Every bounded graph operation has a direct geometric contract test."""
import pytest
from vehiclerecon.surfaces.builder import Graph,OPERATIONS
from vehiclerecon.surfaces.curves import Vector

@pytest.mark.parametrize('operation',sorted(OPERATIONS))
def test_operation_contract(operation):
    def n(id,op,parameters,deps=()):return {'id':id,'op':op,'parameters':parameters,'dependencies':list(deps)}
    a=[(0,0,0),(1,0,0)];b=[(0,1,0),(1,1,0)]
    nodes=[n('a','polyline',{'points':a}),n('b','polyline',{'points':b}),n('point','curve_sample',{'curve':'a','t':.25},['a'])]
    specs={
        'polyline':({'points':a},[],(.3,0,0)),
        'chord_hermite':({'points':a},[],(.3,0,0)),
        'shape_preserving_hermite':({'points':a},[],(.3,0,0)),
        'bezier_rail_range':({'curve':'guide','x_range':[0,1]},[],(.3,0,0)),
        'curve_sample':({'curve':'a','t':.25},['a'],(.25,0,0)),
        'lerp':({'a':'a','b':'b'},['a','b'],(.3,.7,0)),
        'offset':({'source':'a','offset':[0,1,0]},['a'],(.3,1,0)),
        'coons':({'bottom':'a','top':'b'},['a','b'],(.3,.7,0)),
        'cubic_boundary_roll':({'inner':'a','outer':'b','first_control_scale':[.5,0,.75],'second_scale':.65,'slopes':[0,.2]},['a','b'],None),
        'arch_annulus':({'inner_points':a,'outer_points':b,'first_control_scale':[.5,0,.75],'second_scale':.65,'slopes':[0,.2]},[],None),
        'ribbon':({'curve':'a','start_offset':[0,0,0],'end_offset':[0,1,0]},['a'],(.3,.7,0)),
        'bilinear_patch':({'points':[(0,0,0),(1,0,0),(1,1,0),(0,1,0)]},[],(.3,.7,0)),
        'boundary_stitch':({'bottom':a,'top':b,'rows':[.5,1]},[],None)}
    parameters,deps,expected=specs[operation];nodes.append(n('result',operation,parameters,deps))
    curve=[{'co':Vector((0,0,0)),'left':Vector((0,0,0)),'right':Vector((1/3,0,0))},
           {'co':Vector((1,0,0)),'left':Vector((2/3,0,0)),'right':Vector((1,0,0))}]
    result=Graph({'nodes':nodes},{'guide':curve}).get('result')
    if operation=='boundary_stitch':
        vertices,faces=result
        assert len(vertices)==6 and len(faces)==2 and vertices[-1]==(1,1,0)
    elif operation=='curve_sample':assert result==pytest.approx(expected)
    elif operation in ['cubic_boundary_roll','arch_annulus']:
        assert result(.3,0)==pytest.approx((.3,0,0))
        assert result(.3,1)==pytest.approx((.3,1,0))
        assert 0<=result(.3,.7).y<=1
    elif operation in ['coons','lerp','ribbon','bilinear_patch']:assert result(.3,.7)==pytest.approx(expected)
    else:assert result(.3)==pytest.approx(expected,abs=1e-7)
