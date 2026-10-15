import copy
import pytest
from vehiclerecon.core.project import Project,REPOSITORY
from vehiclerecon.core.errors import SchemaError, ReferenceError
from vehiclerecon.reference.calibration import load
from vehiclerecon.reference.transforms import CalibrationTransform
from vehiclerecon.reference.panels import select_panel

@pytest.fixture
def calibration():
    return load(Project(REPOSITORY/'projects/tesla'))

@pytest.mark.parametrize('view',['front','side','rear','top'])
@pytest.mark.parametrize('point',[(0,0),(500.3,700.8),(1536,1152)])
def test_roundtrip(calibration,view,point):
    _,transform=calibration
    assert transform.world_to_pixel(view,*transform.pixel_to_world(view,*point)) == pytest.approx(point,abs=1e-9)

def test_singular(calibration):
    config=copy.deepcopy(calibration[0]);config['views']['side']['v_basis']=config['views']['side']['u_basis']
    with pytest.raises(SchemaError):CalibrationTransform(config)

def test_nonfinite(calibration):
    config=copy.deepcopy(calibration[0]);config['views']['top']['origin'][0]=float('inf')
    with pytest.raises(SchemaError):CalibrationTransform(config)

def test_common_landmarks(calibration):
    config,transform=calibration
    side=config['views']['side']['landmarks']
    for name,record in side.items():
        if name.endswith('_ground'):
            assert transform.pixel_to_world('side',*record)[2] == pytest.approx(0)

def test_prefer_separate(tmp_path,calibration):
    from types import SimpleNamespace
    from vehiclerecon.reference.panels import png_size
    import shutil
    source=REPOSITORY/'tests/fixtures/tesla/legacy_source/refs/crop_front.png'
    shutil.copyfile(source,tmp_path/'front.png')
    fake=SimpleNamespace(data={'references':{'front':'front.png','multiview':'missing.png'}},path=lambda p,**kw:tmp_path/p)
    path,separate=select_panel(fake,'front',calibration[0]['views']['front'])
    assert separate and path.name=='front.png'
