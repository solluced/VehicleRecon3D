import json,os,shutil
import pytest
from vehiclerecon.core import project
from vehiclerecon.core.errors import SchemaError

def test_schema_cache_uses_exact_bytes_even_with_same_size_and_timestamp(tmp_path,monkeypatch):
    schemas=tmp_path/'schemas';shutil.copytree(project.RESOURCE_ROOT/'schemas',schemas)
    path=schemas/'probe.schema.json'
    value={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'https://vehiclerecon.local/schemas/probe.schema.json','type':'number','minimum':1}
    path.write_text(json.dumps(value));before=path.stat()
    monkeypatch.setattr(project,'RESOURCE_ROOT',tmp_path)
    project.validate(1,'probe');project.validate(2,'probe')
    value['minimum']=2;path.write_text(json.dumps(value));os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
    assert path.stat().st_size==before.st_size
    with pytest.raises(SchemaError):project.validate(1,'probe')
    project.validate(2,'probe')

def test_current_data_still_validates_and_nonfinite_is_never_cached():
    command={'type':'MoveWorldLandmark','world_entity_id':'corner','point':[1,2,3]}
    project.validate(command,'authoring_command')
    with pytest.raises(SchemaError):project.validate({**command,'point':[1,2]},'authoring_command')
    with pytest.raises(SchemaError):project.validate({**command,'point':[1,float('nan'),3]},'authoring_command')
