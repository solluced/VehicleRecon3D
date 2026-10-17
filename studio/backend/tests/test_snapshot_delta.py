import copy
import pytest
from test_multiview import env
from vehiclerecon_studio.deltas import snapshot_delta

def apply(before,d):
    assert before['revision']==d['base_revision']
    obs={o['id']:o for o in before['observations']}
    for ident in d['remove']:obs.pop(ident)
    obs.update({o['id']:o for o in d['upsert']})
    return {**d['metadata'],'observations':[obs[i] for i in d['order']]}

def test_delta_exactly_matches_full_snapshot_through_edit_add_delete_and_history(env):
    _,app,post,_,root=env;reg=app.state.registry;ident=next(iter(reg.projects))
    # First lease creates the session owner even before the first authoring edit.
    owner=reg.leases[ident]['tab'];before=reg.snapshot(ident,owner)
    commands=[{'type':'MoveObservation','observation_id':'obs_roof_side','pixel':[130,80]},
              {'type':'MoveWorldLandmark','world_entity_id':'roof_corner','point':[.1,.5,1]}]
    for command in commands:
        r=post('transactions',commands=[command],response_format='delta')
        assert r.status_code==200,r.text
        delta=r.json()['snapshot_delta'];after=reg.snapshot(ident,owner)
        assert apply(before,delta)==after
        assert 'snapshot' not in r.json()
        before=after
    for op in ('undo','redo'):
        r=post(op,response_format='delta');assert r.status_code==200
        assert apply(before,r.json()['snapshot_delta'])==reg.snapshot(ident,owner)
        before=reg.snapshot(ident,owner)
    obs=copy.deepcopy(before['observations'][0]);obs.update(id='new_source_point',revision=1)
    for command in ({'type':'AddObservation','view':obs['view'],'observation':obs},
                    {'type':'DeleteObservation','observation_id':obs['id']}):
        r=post('transactions',commands=[command],response_format='delta');assert r.status_code==200,r.text
        assert apply(before,r.json()['snapshot_delta'])==reg.snapshot(ident,owner)
        before=reg.snapshot(ident,owner)

def test_presentation_ack_is_small_and_never_weakens_canonical_validation(env):
    _,app,post,_,root=env;reg=app.state.registry;ident=next(iter(reg.projects));before=reg.snapshot(ident)['revision']
    r=post('preferences',preferences={'active_view':'top'},response_format='ack')
    assert r.status_code==200 and r.json()=={'revision':before,'preferences_saved':True}
    assert len(r.content)<200
    r=post('transactions',commands=[{'type':'MoveWorldLandmark','world_entity_id':'roof_corner','point':[1,2]}],response_format='delta')
    assert r.status_code==422 and reg.snapshot(ident)['revision']==before
    assert post('transactions',commands=[{'type':'MoveWorldLandmark','world_entity_id':'roof_corner','point':[1,2,3]}],response_format='ack').status_code==422

def test_delta_does_not_lose_canonical_order_or_unmodified_entities():
    before={'id':'x','revision':'a','observations':[{'id':'a','v':1},{'id':'b','v':2}]}
    after={'id':'x','revision':'b','observations':[{'id':'c','v':3},{'id':'a','v':7}]}
    assert apply(before,snapshot_delta(before,after))==after
