from vehiclerecon.validation.regression import compare_sources
from vehiclerecon.core.errors import GateError
import pytest

def source(n=10):return {'bounds_min':[0,0,0],'bounds_max':[1,1,1],'triangles':n}

def test_physical_regression_stays_strict():
    report=compare_sources({'body':source()},{'body':source(9)},set(),.0001)
    assert report['status']=='FAIL'

def test_overlay_difference_is_explicit():
    report=compare_sources({'body':source(),'wire':source()},{'body':source(),'wire':source(8)},{'wire'},.0001)
    assert report['status']=='PASS'
    assert report['topology_overlays'][0]['current_triangles']==8
    assert report['physical_objects'][0]['current_triangles']==10

def test_missing_object_fails():
    with pytest.raises(GateError):compare_sources({'body':source()},{},set(),.0001)
