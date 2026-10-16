import copy
import json
import shutil
import pytest
from vehiclerecon.core.project import Project, REPOSITORY
from vehiclerecon.core.errors import SchemaError, ReferenceError, ConflictError, BlockedError
from vehiclerecon.core.revisions import revision
from vehiclerecon.core.pipeline import Pipeline, Status
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.authoring.service import AuthoringSession
from vehiclerecon.authoring.reviews import subject, review_status
from vehiclerecon.authoring.readiness import readiness, invalidation
from vehiclerecon.authoring.projection import residual, residual_report, sample_cage, project_world


@pytest.fixture
def root(tmp_path):
    shutil.copytree(REPOSITORY/'tests/fixtures/authoring_v2',tmp_path,dirs_exist_ok=True)
    return tmp_path


def apply(session,*commands):
    return session.apply(list(commands),expected_revision=session.revision)


def accept(root):
    session=AuthoringSession(root)
    for kind,op in [('source','SetSourceDisposition'),('cage','SetCageReview')]:
        apply(session,{'type':op,'decision':'ACCEPTED','reviewer':'Explicit synthetic fixture author',
                       'notes':['Analytical four-view evidence inspected; no vehicle asset acceptance.'],
                       'expected_subject':subject(Workspace(root),kind)})
    return session


def test_point_edits_separate_observation_world_and_undo_redo(root):
    s=AuthoringSession(root);w=Workspace(root);before=s.revision
    measured=copy.deepcopy(w.documents['calibration']);original_world=copy.deepcopy(w.documents['cage'])
    result=apply(s,{'type':'MoveWorldLandmark','world_entity_id':'roof_corner','point':[.2,.5,1]})
    w=Workspace(root)
    assert w.documents['calibration']==measured
    report=residual_report(w.documents['calibration'],w.documents['cage'])
    assert report['status']=='FAIL' and report['summary']['passed']==2
    after=s.revision;s.undo(expected_revision=after)
    assert s.revision==before and Workspace(root).documents['cage']==original_world
    s.redo(expected_revision=s.revision);assert s.revision==after
    result=apply(s,{'type':'MoveObservation','observation_id':'obs_roof_side','pixel':[130,78]})
    assert Workspace(root).documents['cage']['landmarks']['roof_corner']==[.2,.5,1]
    assert 'source' in result['stale']['reviews']


def test_typed_commands_reject_raw_patch_and_broken_delete(root):
    s=AuthoringSession(root);before=s.revision
    for command in ({'type':'MoveWorldLandmark','world_entity_id':'roof_corner','point':[0,0,1],'patch':{}},
                    {'type':'DeleteWorldLandmark','world_entity_id':'roof_corner'},
                    {'type':'DeleteObservation','observation_id':'obs_roof_side'}):
        with pytest.raises((SchemaError,ReferenceError)):
            apply(s,command)
        assert s.revision==before


def test_stable_ids_insert_split_merge_and_correspondence_retarget(root):
    s=AuthoringSession(root);w=Workspace(root)
    obs=copy.deepcopy(w.documents['calibration']['views']['side']['landmarks']['observations'][0]);obs['id']='extra_observation'
    link=copy.deepcopy(w.documents['calibration']['correspondences'][0]);link.update(id='end_binding',observation_id=obs['id'],binding_type='curve_point',world_entity_id='roof_edge',point_id='roof.end',required=False)
    apply(s,{'type':'AddObservation','view':'side','observation':obs},{'type':'BindObservation','correspondence':link})
    apply(s,{'type':'AddSplinePoint','target':'cage','entity_id':'roof_edge','after_point_id':'roof.start','point_id':'new_stable','point':[-.25,.5,1]})
    apply(s,{'type':'SplitSpline','target':'cage','entity_id':'roof_edge','point_id':'roof.middle','new_entity_id':'roof_second'})
    w=Workspace(root);links={l['id']:l for l in w.documents['calibration']['correspondences']}
    assert links['end_binding']['point_id']=='roof.end' and links['end_binding']['world_entity_id']=='roof_second'
    apply(s,{'type':'MoveSplinePoint','target':'cage','entity_id':'roof_second','point_id':'roof.middle','point':[0,.5,1.1]})
    assert Workspace(root).documents['cage']['landmarks']['roof_corner']==[0,.5,1.1]
    apply(s,{'type':'MergeSpline','target':'cage','entity_id':'roof_edge','other_entity_id':'roof_second'})
    ids=Workspace(root).documents['cage']['curves'][0]['point_ids']
    assert ids==['roof.start','new_stable','roof.middle','roof.end']
    before=s.revision
    with pytest.raises(ReferenceError):
        apply(s,{'type':'DeleteSplinePoint','target':'cage','entity_id':'roof_edge','point_id':'roof.end'})
    assert s.revision==before
    apply(s,{'type':'UnbindObservation','correspondence_id':'end_binding'},
          {'type':'DeleteObservation','observation_id':'extra_observation'},
          {'type':'DeleteSplinePoint','target':'cage','entity_id':'roof_edge','point_id':'roof.end'})


def test_source_spline_stable_ids_and_point_move(root):
    s=AuthoringSession(root);o=copy.deepcopy(Workspace(root).documents['calibration']['views']['side']['landmarks']['observations'][0])
    o.pop('pixel');o.update(id='source_spline',kind='spline',points=[{'id':'source_a','pixel':[10,10]},{'id':'source_b','pixel':[20,20]},{'id':'source_c','pixel':[30,30]}])
    apply(s,{'type':'AddObservation','view':'side','observation':o})
    apply(s,{'type':'SplitSpline','target':'observation','entity_id':'source_spline','point_id':'source_b','new_entity_id':'source_second'})
    apply(s,{'type':'MoveSplinePoint','target':'observation','entity_id':'source_second','point_id':'source_b','point':[22,22]})
    apply(s,{'type':'MergeSpline','target':'observation','entity_id':'source_spline','other_entity_id':'source_second'})
    points=next(o for o in Workspace(root).documents['calibration']['views']['side']['landmarks']['observations'] if o['id']=='source_spline')['points']
    assert [p['id'] for p in points]==['source_a','source_b','source_c'] and points[1]['pixel']==[22,22]


def test_measurement_multifile_unknown_and_locked(root):
    s=AuthoringSession(root);before=s.revision
    m={'id':'measure_height','value':None,'unit':'mm','meaning':'body height','provenance':{'type':'approximate','method':'unknown'}}
    r=apply(s,{'type':'SetMeasurement','measurement':m,'dimension':'height_m'})
    assert {f['path'] for f in r['changed_files']}=={'project.json','generated/calibration.json'}
    assert readiness(root)['unknown_dimensions']==['height_m']
    s.undo(expected_revision=s.revision);assert s.revision==before
    m.update(value=1000,locked=True)
    apply(s,{'type':'SetMeasurement','measurement':m})
    m['value']=1001
    with pytest.raises(ConflictError):apply(s,{'type':'SetMeasurement','measurement':m})


def test_tolerance_provenance_revision_conflict_and_observer(root):
    events=[];s=AuthoringSession(root,observer=events.append);before=s.revision
    apply(s,{'type':'SetTolerance','correspondence_id':'link_roof_side','allowed_px':3,'provenance':{'type':'measured','method':'explicit policy revision'}})
    assert events[-1]['kind']=='project_changed'
    with pytest.raises(ConflictError):s.apply([{'type':'MoveWorldLandmark','world_entity_id':'roof_corner','point':[0,.5,1]}],expected_revision=before)
    path=root/'project.json';path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ConflictError):s.undo(expected_revision=events[-1]['revision'])


def test_individual_residuals_projection_and_sampling(root):
    w=Workspace(root);cal=w.documents['calibration'];cage=w.documents['cage']
    assert residual([0,0],[3,4],5)['status']=='PASS'
    assert residual([0,0],[3,4.001],5)['status']=='FAIL'
    assert residual_report(cal,cage)['status']=='PASS'
    assert project_world(cal,'side',[0,.5,1])==pytest.approx([128,78])
    samples=sample_cage(cal,cage,count=5)
    assert len(samples[0]['world_samples'])==5 and samples[0]['control_ids']==['roof.start','roof.middle','roof.end']
    cage['curves'][0]['handles']='AUTO'
    assert sample_cage(cal,cage)[0]['sample_kind']=='control_polygon'


@pytest.mark.parametrize('decision',['NEEDS_CORRECTION','INCONSISTENT_SOURCE'])
def test_source_rejection_blocks_headless_surface_action(root,decision):
    s=AuthoringSession(root)
    apply(s,{'type':'SetSourceDisposition','decision':decision,'reviewer':'Fixture reviewer','notes':['Explicit source rejection.']})
    pipeline=Pipeline(Project(root),use_cache=False);executed=[]
    actions={stage:(lambda stage=stage:executed.append(stage) or []) for stage in ('preflight','references','calibration','overlay','cage','surfaces')}
    assert pipeline.run(actions=actions,until='surfaces')==1
    assert pipeline.results[-1].status==Status.BLOCKED and 'surfaces' not in executed


def test_explicit_acceptance_staleness_and_positive_surface_gate(root):
    s=accept(root);w=Workspace(root)
    assert review_status(w,'source')['state']==review_status(w,'cage')['state']=='READY'
    pipeline=Pipeline(Project(root),use_cache=False)
    stages=['preflight','references','calibration','overlay','cage','surfaces'];executed=[]
    assert pipeline.run(actions={stage:(lambda stage=stage:executed.append(stage) or []) for stage in stages},until='surfaces')==0
    assert executed==stages
    apply(s,{'type':'MoveWorldLandmark','world_entity_id':'roof_corner','point':[.1,.5,1]})
    w=Workspace(root)
    assert review_status(w,'source')['state']=='READY' and review_status(w,'cage')['current'] is False
    with pytest.raises(BlockedError):
        apply(s,{'type':'SetCageReview','decision':'ACCEPTED','reviewer':'Reviewer','notes':['Cannot override an individual failure.'],'expected_subject':subject(w,'cage')})
    apply(s,{'type':'MoveObservation','observation_id':'obs_roof_top','pixel':[129,103]})
    assert not review_status(Workspace(root),'source')['current']


def test_candidate_anchor_commands_do_not_activate_calibration(root):
    s=AuthoringSession(root);before=(root/'generated/calibration.json').read_bytes()
    model={'type':'piecewise_monotonic','axis':'u','image_domain_px':[0,100],'affine_domain_px':[0,100],
           'anchors':[{'image':0,'world_normalized':0,'semantic':'front_axle'},{'image':1,'world_normalized':1,'semantic':'rear_axle'}],'max_scale_change':.1}
    apply(s,{'type':'AddRectificationAnchor','candidate_id':'candidate_one','view':'top','rectification':model,
             'anchor':{'image':.5,'world_normalized':.8,'semantic':'roof_corner'}})
    assert (root/'generated/calibration.json').read_bytes()==before
    assert 'rectification' not in Workspace(root).documents['calibration']['views']['top']
    apply(s,{'type':'RemoveRectificationAnchor','candidate_id':'candidate_one','semantic':'roof_corner'})
    with pytest.raises(ConflictError):apply(s,{'type':'RemoveRectificationAnchor','candidate_id':'candidate_one','semantic':'front_axle'})


def test_stale_scope_and_draft_readiness_are_not_builds(root,tmp_path):
    assert invalidation(['viewer'])['geometry_remains_valid']
    assert 'surfaces' not in invalidation(['viewer'])['stages']
    assert 'source' not in invalidation(['world'])['reviews']
    r=readiness(root)
    assert r['calibration']['state']=='READY' and r['surfaces']['state']=='BLOCKED'
    assert not (root/'.cache/surfaces.blend').exists()


def test_proof_replacement_cannot_retarget_explicit_review(root):
    s=AuthoringSession(root);proof=root/'validation/proof.png';proof.parent.mkdir(exist_ok=True)
    proof.write_bytes((root/'input/reference.png').read_bytes())
    policy=copy.deepcopy(Workspace(root).documents['calibration']['authoring_policy']);policy['required_proofs']=['validation/proof.png']
    apply(s,{'type':'SetCoveragePolicy','policy':policy})
    inspected=subject(Workspace(root),'source');proof.write_bytes(proof.read_bytes()+b'new artifact')
    with pytest.raises(ConflictError):
        apply(s,{'type':'SetSourceDisposition','decision':'ACCEPTED','reviewer':'Reviewer','notes':['Old image inspected.'],'expected_subject':inspected})


def test_settings_cannot_commit_export_policy_that_next_open_rejects(root):
    s=AuthoringSession(root);before=s.revision
    export=copy.deepcopy(Project(REPOSITORY/'projects/tesla').data['export'])
    export['excluded_collections'].append(export['collections'][0])
    with pytest.raises(SchemaError,match='cannot be excluded'):
        apply(s,{'type':'SetProjectSettings','section':'export','value':export})
    assert s.revision==before
    assert Project(root).data['schema_version']==2
