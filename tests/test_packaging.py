import json,subprocess,sys,zipfile,shutil
from pathlib import Path
import pytest
from vehiclerecon.core.project import REPOSITORY

@pytest.mark.blender
def test_installed_wheel_resources_and_worker(tmp_path):
    dist=tmp_path/'dist'
    result=subprocess.run([sys.executable,'-m','build','--wheel','--no-isolation','--outdir',str(dist)],cwd=REPOSITORY,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    wheel=next(dist.glob('*.whl'))
    with zipfile.ZipFile(wheel) as archive:
        names=archive.namelist()
        assert 'vehiclerecon/viewer/viewer_template.html' in names
        assert 'vehiclerecon/viewer/test_viewer.mjs' in names
        assert any(n.endswith('/share/vehiclerecon/schemas/project.schema.json') for n in names)
        assert not any(n.startswith(('projects/','tests/','scripts/')) for n in names)
    target=tmp_path/'installed'
    result=subprocess.run([sys.executable,'-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(target),str(wheel)],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    project=tmp_path/'project';project.mkdir()
    source=REPOSITORY/'projects/tesla'
    shutil.copyfile(source/'project.json',project/'project.json')
    for folder in ['input','generated']:shutil.copytree(source/folder,project/folder)
    code=f"import sys;sys.path.insert(0,{str(target)!r});from vehiclerecon.core.project import Project,RESOURCE_ROOT;from vehiclerecon.blender.runner import run;p=Project({str(project)!r});print(RESOURCE_ROOT);run(p,'initialize');run(p,'calibration');print('INSTALLED_WORKER_PASS')"
    result=subprocess.run([sys.executable,'-I','-c',code],cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'INSTALLED_WORKER_PASS' in result.stdout
    assert (project/'.cache/initialize.blend').is_file()
    assert (project/'validation/reference_alignment.png').is_file()
    report=json.loads((project/'validation/initialize_report.json').read_text())
    assert Path(report['package_file']).is_relative_to(target)
    assert Path(report['resource_root']).is_relative_to(target)
