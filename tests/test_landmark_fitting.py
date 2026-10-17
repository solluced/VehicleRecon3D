import copy
import json
from pathlib import Path
import pytest
from vehiclerecon.authoring.fitting import fit_landmark,place_on_plane
from vehiclerecon.authoring.projection import project_world
from vehiclerecon.authoring.consistency import analyze,heat
from vehiclerecon.core.errors import SchemaError


@pytest.fixture
def data():
    root=Path(__file__).parent/'fixtures/authoring_v2/generated'
    return json.loads((root/'calibration.json').read_text()),json.loads((root/'cage.json').read_text())


def test_four_views_recover_exact_known_xyz_without_mutation(data):
    cal,cage=data;before=copy.deepcopy(cal)
    result=fit_landmark(cal,['obs_roof_'+v for v in ('side','top','front','rear')])
    assert result['status']=='PASS' and result['proposed_xyz']==pytest.approx([0,.5,1],abs=1e-10)
    assert result['conditioning']['rank']==3 and result['max_residual_px']<1e-8
    assert cal==before and cage['landmarks']['roof_corner']==[0,.5,1]


def test_single_view_depth_is_never_invented_and_plane_must_intersect(data):
    cal,_=data
    assert fit_landmark(cal,['obs_roof_side'])['status']=='UNDERCONSTRAINED'
    result=fit_landmark(cal,['obs_roof_side'],constraints=[{'axis':'Y','value':.5}])
    assert result['status']=='PASS' and result['proposed_xyz']==pytest.approx([0,.5,1])
    assert place_on_plane(cal,'side',[128,78],[0,1,0],.5)==pytest.approx([0,.5,1])
    with pytest.raises(SchemaError):place_on_plane(cal,'side',[128,78],[0,0,1],1)


def test_parallel_views_stay_ambiguous_and_conflicting_constraints_fail(data):
    cal,_=data;cal['views']['top'].update({k:cal['views']['side'][k] for k in ('origin','u_basis','v_basis')})
    assert fit_landmark(cal,['obs_roof_side','obs_roof_top'])['status']=='UNDERCONSTRAINED'
    with pytest.raises(SchemaError):fit_landmark(cal,['obs_roof_side'],constraints=[{'axis':'Y','value':0},{'axis':'Y','value':1}])


def test_outlier_is_not_hidden_by_robust_fit_or_optional_mean(data):
    cal,_=data;cal['views']['top']['landmarks']['observations'][0]['pixel'][0]+=40
    result=fit_landmark(cal,['obs_roof_'+v for v in ('side','top','front','rear')])
    assert result['status']=='FAIL' and result['max_residual_px']>19
    assert any(r['status']=='FAIL' for r in result['rows'])
    assert len(result['observations_used'])==4


def test_explicit_exclusions_and_inferred_evidence_are_reported(data):
    cal,_=data;cal['views']['rear']['landmarks']['observations'][0].update(visibility='inferred',measured=False)
    result=fit_landmark(cal,['obs_roof_'+v for v in ('side','top','front','rear')],excluded_ids=['obs_roof_front'])
    assert result['status']=='PASS' and len(result['observations_excluded'])==2


def test_rectified_model_fits_original_pixels_with_shared_transform(data):
    cal,_=data;cal['views']['top']['rectification']={'type':'piecewise_monotonic','axis':'u','image_domain_px':[0,256],'affine_domain_px':[0,256],
        'anchors':[{'image':0,'world_normalized':0},{'image':.5,'world_normalized':.51},{'image':1,'world_normalized':1}],'max_scale_change':.1}
    cal['views']['top']['landmarks']['observations'][0]['pixel']=list(project_world(cal,'top',[0,.5,1]))
    result=fit_landmark(cal,['obs_roof_side','obs_roof_top'])
    assert result['status']=='PASS' and result['proposed_xyz']==pytest.approx([0,.5,1],abs=1e-9)


def test_shared_analysis_heat_coverage_samples_and_axle_diagnostic(data):
    cal,cage=data;result=analyze(cal,cage)
    assert result['residuals']['status']=='PASS'
    assert result['coverage'][0]['views']==dict.fromkeys(('front','side','rear','top'),1)
    assert result['wheelbase']['difference_m']==0
    assert result['scene']['curves'][0]['world_samples']
    assert heat({'residual_px':1.8,'allowed_tolerance_px':2})['heat']=='NEAR'
    assert heat({'residual_px':2.1,'allowed_tolerance_px':2})['heat']=='FAIL'
    assert heat({'residual_px':None,'allowed_tolerance_px':2})['heat']=='UNKNOWN'


def test_helper_reference_is_not_silently_projected_as_the_calibrated_source(data):
    from vehiclerecon.authoring.projection import residual_report
    cal,cage=data
    cal['views']['top']['landmarks']['observations'][0]['source_sha256']='0'*64
    result=fit_landmark(cal,['obs_roof_side','obs_roof_top'])
    assert result['status']=='UNDERCONSTRAINED'
    assert 'registration' in result['observations_excluded'][0]['reason']
    report=residual_report(cal,cage)
    assert report['status']=='BLOCKED' and report['coverage']['state']=='BLOCKED'
