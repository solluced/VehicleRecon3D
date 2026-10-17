import copy
import json
import pytest
from jsonschema import Draft202012Validator
from referencing import Registry,Resource
from vehiclerecon.core.project import RESOURCE_ROOT
from vehiclerecon.core.schema_dispatch import authoring_validator


def test_authoring_dispatch_matches_full_draft_for_invalid_fields_and_discriminators():
    schemas=[json.loads(p.read_text()) for p in (RESOURCE_ROOT/'schemas').glob('*.schema.json')]
    registry=Registry().with_resources((s['$id'],Resource.from_contents(s)) for s in schemas)
    schema=next(s for s in schemas if s['$id'].endswith('/authoring.schema.json'))['$defs']['observation']
    base={'id':'point_one','view':'side','kind':'point','semantic_role':'roof','reference_id':'multiview','source_sha256':'a'*64,'crop_id':'b'*64,
          'revision':1,'provenance':{'type':'measured','method':'test'},'uncertainty_px':1,'visibility':'observed','measured':True,'pixel':[1,2]}
    candidates=[base]
    for kind in ['polyline','spline','axis','circle','measurement']:
        o=copy.deepcopy(base);o.pop('pixel');o['kind']=kind
        if kind in ('polyline','spline','axis'):o['points']=[{'id':'a','pixel':[1,2]},{'id':'b','pixel':[3,4]}]
        elif kind=='circle':o.update(center=[1,2],radius_px=4)
        else:o['measurement_id']='length'
        candidates.append(o)
    all_cases=[]
    for o in candidates:
        all_cases.append(o)
        for key in o:
            c=copy.deepcopy(o);c.pop(key);all_cases.append(c)
            for bad in (None,False,[],{},'unknown'):
                c=copy.deepcopy(o);c[key]=bad;all_cases.append(c)
        all_cases.append({**o,'unsupported_field':1})
    reference=Draft202012Validator(schema,registry=registry);fast=authoring_validator()(schema,registry=registry)
    for value in all_cases:assert fast.is_valid(value)==reference.is_valid(value),value


@pytest.mark.parametrize('schema,value',[
    ({'oneOf':[{'type':'object','properties':{'kind':{'const':'a'}}},{'type':'object','properties':{'kind':{'const':'a'}}}]},{'kind':'a'}),
    ({'oneOf':[{'type':'object','required':['kind'],'properties':{'kind':{'const':'a'}}},{'type':'number'}]},3),
    ({'oneOf':[{'required':['kind'],'properties':{'kind':{'const':'a'}}},{'required':['kind'],'properties':{'kind':{'const':'b'}}}]},{'kind':'missing'}),
])
def test_ambiguous_unknown_or_untyped_unions_use_full_semantics(schema,value):
    assert authoring_validator()(schema).is_valid(value)==Draft202012Validator(schema).is_valid(value)


def test_structural_cache_checks_data_and_referenced_schema_identity():
    from vehiclerecon.core.schema_dispatch import validation_namespace
    schema={'oneOf':[{'type':'object','required':['kind','value'],'properties':{'kind':{'const':'a'},'value':{'$ref':'https://test/number'}}},
                     {'type':'object','required':['kind'],'properties':{'kind':{'const':'b'}}}]}
    def validator(minimum):
        ref={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'https://test/number','type':'number','minimum':minimum}
        registry=Registry().with_resource(ref['$id'],Resource.from_contents(ref))
        return authoring_validator()(schema,registry=registry),ref
    value={'kind':'a','value':3};v,ref=validator(0)
    with validation_namespace([schema,ref]):
        assert v.is_valid(value) and v.is_valid(value)
        assert not v.is_valid({'kind':'a','value':-1})
    v,ref=validator(5)
    with validation_namespace([schema,ref]):assert not v.is_valid(value)
