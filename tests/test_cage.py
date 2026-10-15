import copy
import pytest
from vehiclerecon.core.project import Project,REPOSITORY,validate
from vehiclerecon.core.errors import SchemaError,ReferenceError
from vehiclerecon.cage.builder import records
from vehiclerecon.cage.curves import mirrored,expand
from vehiclerecon.cage.sections import full_section
from vehiclerecon.cage.schema import check

def data():
    p=Project(REPOSITORY/'projects/tesla')
    return p.generated('cage'),p.generated('calibration')['wheel_geometry']

def test_count_and_ids():
    c,g=data();result=check(c,g)
    assert len(result)==53
    assert len({r['id'] for r in result})==53

def test_symmetry():
    c,g=data();result={r['id']:r for r in check(c,g)}
    for r in c['curves']:
        if r['symmetry']:
            assert result[r['id']+'_L']['points']==mirrored(result[r['id']+'_R']['points'])

def test_winding():
    points=[(0,0,1),(0,1,1),(0,1,0)]
    assert full_section(points)==[(0,-1,0),(0,-1,1),*points]
    assert mirrored(points,reverse=True)==[(0,-1,0),(0,-1,1),(0,0,1)]

def test_unresolved():
    c,g=data();c['curves'][0]['landmark']='absent'
    with pytest.raises(ReferenceError):check(c,g)

def test_bad_coordinates():
    c,g=data();c['curves'][0]['points'][0][0]=float('nan')
    with pytest.raises(SchemaError):check(c,g)

def test_cardinality():
    c,g=data();c['curves'][0]['points']=[]
    with pytest.raises(SchemaError):check(c,g)

def test_duplicate():
    c,g=data();c['curves'].append(copy.deepcopy(c['curves'][0]))
    with pytest.raises(SchemaError):check(c,g)

def test_missing_axle():
    c,g=data();c['guides'][0]['axles']=['absent']
    with pytest.raises(ReferenceError):check(c,g)
