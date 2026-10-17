import numpy as np
import pytest
from vehiclerecon.authoring.contours import fit_contour

def test_pixel_simplification_and_spline_have_continuous_bounds_and_endpoints():
    p=np.column_stack((np.linspace(0,200,1001),30*np.sin(np.linspace(0,3,1001))))
    for spline in (False,True):
        fit=fit_contour(p,tolerance=.8,max_points=128,spline=spline)
        assert fit['points'][0]==p[0].tolist() and fit['points'][-1]==p[-1].tolist()
        assert fit['fit']['certified_max_deviation_px']<=.8
        assert fit['fit']['max_deviation_px']<=.8+.025
        assert 2<len(fit['points'])<len(p)
        assert fit['original_points']==p.tolist()
        if spline:assert len(fit['knots'])==len(fit['points'])

def test_corners_closed_paths_and_point_cap_never_override_error():
    p=[[0,0],[50,0],[50,30],[0,30],[0,0]]
    fit=fit_contour(p,tolerance=.2,closed=True,spline=True)
    assert fit['points']==p and fit['fit']['certified_max_deviation_px']<=.2
    with pytest.raises(ValueError,match='budget'):fit_contour(p,tolerance=.2,closed=True,max_points=3)
    with pytest.raises(ValueError):fit_contour([[1,1],[1,1]])
    with pytest.raises(ValueError):fit_contour([[0,0],[float('nan'),0]])

def test_highly_curved_interval_certificate_controls_spline_overshoot():
    p=np.column_stack((np.linspace(0,100,600),20*np.sin(np.linspace(0,12,600))))
    fit=fit_contour(p,tolerance=.3,spline=True,preserve_corners=False)
    assert fit['fit']['certified_max_deviation_px']<=.3
    assert fit['fit']['max_deviation_px']<=.325
