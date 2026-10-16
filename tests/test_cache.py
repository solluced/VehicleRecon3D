"""Dependency invalidation uses mocked build actions; review gates have separate live tests."""
import copy,shutil
from types import MethodType
import pytest
from vehiclerecon.core.project import Project,REPOSITORY,read_json
from vehiclerecon.core.manifest import write_json,digest_file
from vehiclerecon.core.cache import StageCache
from vehiclerecon.core.pipeline import Pipeline,Status

@pytest.fixture
def project(tmp_path):
    source=REPOSITORY/'projects/tesla'
    for folder in ['input','generated']:shutil.copytree(source/folder,tmp_path/folder)
    shutil.copyfile(source/'project.json',tmp_path/'project.json')
    p=Project(tmp_path)
    for relative in ['validation/geometry_audit.json','validation/review.json',*p.data['presentation']['review_proofs']]:
        target=p.path(relative);target.parent.mkdir(exist_ok=True);shutil.copyfile(source/relative,target)
    from vehiclerecon.validation.report import record_review
    record_review(p,reviewer='Mocked cache test fixture',decision='PASS',
                  notes=['Explicit synthetic decision for dependency tests, not a production visual review.'],limitations=[])
    return p

def fake_pipeline(project):
    pipeline=Pipeline(project,implementation='unit-cache-version')
    counts={}
    def execute(self,stage):
        if stage=='preflight':return []
        counts[stage]=counts.get(stage,0)+1
        if stage=='delivery':
            write_json(project.path('output/delivery_manifest.json'),{'status':'PASS','files':[{'path':'project.json','sha256':digest_file(project.path('project.json'))}]})
            return ['output/delivery_manifest.json']
        path=f'.cache/unit_artifacts/{stage}.txt';target=project.path(path);target.parent.mkdir(exist_ok=True)
        target.write_text(stage+str(counts[stage]))
        return [path]
    pipeline.execute=MethodType(execute,pipeline)
    return pipeline,counts

def test_verified_cache_skips(project):
    pipeline,counts=fake_pipeline(project)
    assert pipeline.run()==0
    assert pipeline.run()==0
    assert all(r.status==Status.SKIP for r in pipeline.results[1:])
    assert all(count==1 for count in counts.values())

def test_viewer_label_only_rebuilds_viewer_delivery(project):
    pipeline,counts=fake_pipeline(project);assert pipeline.run()==0
    project.data['viewer']['title']='Another label'
    assert pipeline.run()==0
    assert {k for k,v in counts.items() if v==2}=={'viewer','delivery'}

def test_lights_only_preserve_surfaces(project):
    pipeline,counts=fake_pipeline(project);assert pipeline.run()==0
    path=project.path(project.data['generated']['details']);data=read_json(path)
    data['components'][0]['parameters']['offset'][0]+=.001;write_json(path,data)
    assert pipeline.run()==0
    assert counts['surfaces']==1 and counts['cage']==1 and counts['calibration']==1
    assert all(counts[k]==2 for k in ['details','geometry','presentation','export','glb_verify','viewer','delivery'])

def test_cage_changes_invalidate_downstream(project):
    pipeline,counts=fake_pipeline(project);assert pipeline.run()==0
    path=project.path(project.data['generated']['cage']);data=read_json(path)
    data['curves'][0]['points'][0][0]+=.01;write_json(path,data)
    assert pipeline.run()==0
    assert counts['calibration']==1 and counts['cage']==2 and counts['surfaces']==2

def test_calibration_changes_invalidate_cage(project):
    pipeline,counts=fake_pipeline(project);assert pipeline.run()==0
    path=project.path(project.data['generated']['calibration']);data=read_json(path)
    data['uncertainty']['landmark_px']+=1;write_json(path,data)
    assert pipeline.run()==0
    assert counts['calibration']==2 and counts['cage']==2 and counts['surfaces']==2

def test_rectification_changes_invalidate_projection_and_downstream(project):
    pipeline,counts=fake_pipeline(project);assert pipeline.run()==0
    path=project.path(project.data['generated']['calibration']);data=read_json(path)
    data['views']['top']['rectification']={
        'type':'piecewise_monotonic','axis':'u',
        'image_domain_px':[0,1000],'affine_domain_px':[0,1000],
        'anchors':[{'image':x,'world_normalized':y,'semantic':name}
                   for x,y,name in [(0,0,'start'),(.5,.51,'feature'),(1,1,'end')]]}
    write_json(path,data)
    assert pipeline.run()==0
    assert counts['references']==1 and counts['overlay']==1
    assert all(counts[k]==2 for k in ['calibration','cage','surfaces','silhouette','details',
                                    'geometry','presentation','export','glb_verify','viewer','delivery'])
    data['views']['top']['rectification']['anchors'][1]['world_normalized']=.515
    write_json(path,data)
    assert pipeline.run()==0
    assert counts['calibration']==3 and counts['cage']==3

def test_corrupt_and_missing_outputs_are_not_hits(project):
    cache=StageCache(project,'unit');key=cache.key('surfaces',{'x':1},{'cage':'parent'})
    path=project.path('.cache/proof.txt');path.write_text('good')
    cache.store('surfaces',key,['.cache/proof.txt'],{'cage':'parent'},{'x':1})
    assert cache.hit('surfaces',key)
    path.write_text('corrupt');assert cache.hit('surfaces',key) is None
    path.unlink();assert cache.hit('surfaces',key) is None

def test_dependency_output_change_propagates(project):
    pipeline,counts=fake_pipeline(project);assert pipeline.run()==0
    project.path('.cache/unit_artifacts/surfaces.txt').write_text('corrupt')
    assert pipeline.run()==0
    assert counts['surfaces']==2 and counts['details']==2

def test_implementation_and_dependency_keys(project):
    a=StageCache(project,'version-a');b=StageCache(project,'version-b')
    assert a.key('cage',{}, {})!=b.key('cage',{}, {})
    assert a.key('cage',{}, {'calibration':'a'})!=a.key('cage',{}, {'calibration':'b'})
    assert a.key('cage',{'x':1,'y':2},{})==a.key('cage',{'y':2,'x':1},{})

def test_role_bindings_invalidate_audit_not_geometry_construction(project):
    pipeline,counts=fake_pipeline(project);assert pipeline.run()==0
    project.data['roles']['hood']=['another_surface']
    assert pipeline.run()==0
    assert counts['surfaces']==1 and counts['details']==1
    assert counts['geometry']==2 and counts['presentation']==2
