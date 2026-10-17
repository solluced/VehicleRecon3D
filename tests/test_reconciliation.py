import copy,json
import pytest
from reconciliation_fixture import prepare
from vehiclerecon.core.project import validate
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.authoring.service import AuthoringSession
from vehiclerecon.core.revisions import snapshot
from vehiclerecon.core.errors import ReconError
from vehiclerecon.reference.reconciliation import make_candidate,evaluate,current
from vehiclerecon.reference.rectification import AxisRectification,PiecewiseMonotonicAxisWarp

def payload(p):return {k:p[k] for k in ('id','status','source_revision','base_calibration_hash','source_hashes','creator','request')}

def test_positive_heldout_activation_and_exact_undo(tmp_path):
    req=prepare(tmp_path/'study');session=AuthoringSession(tmp_path/'study');w=Workspace(session.root)
    p=make_candidate(w,req,ident='positive',creator='Fixture author');r=evaluate(p)
    assert r['eligible'],r['reasons']
    assert r['before']['failed_critical']>0 and r['after']['failed_critical']==0
    assert r['after']['held_out_rms_px']<1e-9 and len(r['held_out'])>=3
    assert .9<=r['local_scale_range'][0]<=r['local_scale_range'][1]<=1.1
    before=snapshot(session.root);world=copy.deepcopy(w.documents['cage'])
    command={'type':'ActivateRectification','candidate':payload(p)};validate(command,'authoring_command')
    result=session.apply([command],expected_revision=session.revision)
    assert 'rectification' in Workspace(session.root).documents['calibration']['views']['top']
    assert Workspace(session.root).documents['cage']==world
    assert result['stale']['reviews']==['cage','final','source']
    session.undo(expected_revision=session.revision);assert snapshot(session.root)==before

@pytest.mark.parametrize('mutation',['duplicate','reversed','scale','unlocked','heldout_fitted','extrapolation'])
def test_invalid_candidates_never_activate(tmp_path,mutation):
    req=prepare(tmp_path/'study');p=make_candidate(Workspace(tmp_path/'study'),req,ident='bad',creator='Tester')
    if mutation=='duplicate':p['request']['anchors'][2]['image']=p['request']['anchors'][0]['image']
    if mutation=='reversed':p['request']['anchors'][2]['world_normalized']=-1
    if mutation=='scale':p['request']['anchors'][2]['world_normalized']+=.1
    if mutation=='unlocked':p['request']['anchors'][0]['locked']=False
    if mutation=='heldout_fitted':
        for a in p['request']['anchors']:a['role']='FIT'
    if mutation=='extrapolation':p['crop']=[0,0,256,256]
    assert not evaluate(p)['eligible']
    session=AuthoringSession(tmp_path/'study');before=snapshot(session.root)
    if mutation=='extrapolation':p['request']['allow_extrapolation']=False;p['request']['image_domain_px']=[60,200]
    with pytest.raises(ReconError):session.apply([{'type':'ActivateRectification','candidate':payload(p)}],expected_revision=session.revision)
    assert snapshot(session.root)==before

def test_exact_scale_boundary_and_analytic_extrema():
    for y,valid in [(.525-1e-8,True),(.525,True),(.525+1e-8,False)]:
        config={'type':'piecewise_monotonic','axis':'u','image_domain_px':[0,1],'affine_domain_px':[0,1],
            'anchors':[{'image':x,'world_normalized':v,'semantic':str(x)} for x,v in [(0,0),(.5,y),(1,1)]],'max_scale_change':.1}
        if valid:AxisRectification(config)
        else:
            with pytest.raises(ReconError):AxisRectification(config)
        warp=PiecewiseMonotonicAxisWarp([0,.5,1],[0,y,1]);ext=warp.derivative_extrema()
        assert (ext['minimum']['derivative'],ext['maximum']['derivative'])==pytest.approx(warp.derivative_range())

def test_stale_source_crop_and_calibration_cannot_activate(tmp_path):
    req=prepare(tmp_path/'study');w=Workspace(tmp_path/'study');p=make_candidate(w,req,ident='stale',creator='Tester')
    assert current(w,p)
    (w.root/'input/reference.png').write_bytes((w.root/'input/reference.png').read_bytes()+b'\n')
    assert not current(w,p)

def test_individual_heldout_failure_is_not_averaged_away(tmp_path):
    req=prepare(tmp_path/'study');p=make_candidate(Workspace(tmp_path/'study'),req,ident='heldout',creator='Tester')
    row=next(e for e in p['evidence'] if e['observation_id']==next(a['observation_id'] for a in req['anchors'] if a['role']=='HELD_OUT'))
    row['pixel'][1]+=1
    result=evaluate(p)
    assert not result['eligible'] and any(e['status']=='FAIL' for e in result['held_out'])
    assert any('Held-out residual fails' in reason for reason in result['reasons'])

def test_crop_calibration_staleness_and_candidate_comparison(tmp_path):
    req=prepare(tmp_path/'study');w=Workspace(tmp_path/'study');p=make_candidate(w,req,ident='compare',creator='Tester')
    other=copy.deepcopy(p);other['request']['anchors'][2]['world_normalized']+=.002
    assert evaluate(p)['whole_crop']!=evaluate(other)['whole_crop']
    w.documents['calibration']['views']['top']['crop'][0]+=1
    assert not current(w,p)
    w.documents['calibration']['views']['top']['crop'][0]-=1
    w.documents['calibration']['views']['top']['origin'][0]+=.01
    assert not current(w,p)

def test_domain_order_rejected_as_validation_error(tmp_path):
    req=prepare(tmp_path/'study');p=make_candidate(Workspace(tmp_path/'study'),req,ident='domain',creator='Tester')
    for domain in ([100,100],[100,0]):
        p['request']['image_domain_px']=domain
        assert not evaluate(p)['eligible']
