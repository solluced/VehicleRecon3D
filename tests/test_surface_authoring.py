"""Independent bounded surfaces: contracts, atomic commands, gates and real mesh checks."""
import copy
import json
import shutil
import pytest
from vehiclerecon.core.project import REPOSITORY, validate, full_validation
from vehiclerecon.core.errors import ReconError, BlockedError, ConflictError
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.authoring.service import AuthoringSession
from vehiclerecon.surfaces.authoring import registry, dependencies, graph_contract
from vehiclerecon.surfaces.builder import Graph, OPERATIONS
from vehiclerecon.surfaces.preview import evaluate, PreviewCache, inspect


@pytest.fixture
def root(tmp_path):
    shutil.copytree(REPOSITORY/'tests/fixtures/surface_authoring_v2',tmp_path,dirs_exist_ok=True)
    return tmp_path


def apply(s,*commands):return s.apply(list(commands),expected_revision=s.revision)
def graph(root):return copy.deepcopy(Workspace(root).documents['surface_graph'])


def test_registry_matches_production_schema_and_positive_fixture(root):
    assert {r['id'] for r in registry()['operations']}==OPERATIONS
    w=Workspace(root);g=graph(root)
    with full_validation():graph_contract(g,w.documents['cage'])
    a=evaluate(w);b=evaluate(w)
    assert a['status']=='PASS' and a['certified_current']
    assert a['patches']==b['patches'] and a['adjacency'][0]['max_gap_m']==0
    assert a['adjacency'][0]['normal_angle_max_deg']==0
    assert len(a['patches'][0]['triangles'])==128
    assert all(c['gap_m']==0 for rows in a['corners'].values() for c in rows)
    assert a['self_intersection'].startswith('NOT TESTED')


def test_typed_graph_commands_exact_undo_and_stable_identity(root):
    s=AuthoringSession(root);before=graph(root)
    apply(s,{'type':'AddSurfacePatch','patch_id':'new.panel','node_id':'new.sample','name':'Draft','semantic_role':'panel','op':'coons'})
    assert graph(root)['nodes'][-1]['draft']
    assert evaluate(Workspace(root))['certified_current'] is False
    for slot,source in dict(bottom='bottom.a',top='top.a',left='left',right='shared').items():
        apply(s,dict(type='SetSurfaceBoundary',node_id='new.sample',boundary=slot,source=source))
    apply(s,dict(type='SetSurfaceDraft',node_id='new.sample',draft=False))
    assert evaluate(Workspace(root))['status']=='PASS'
    canonical=(root/'generated/surface_graph.json').read_bytes()
    for command in [dict(type='SetSurfaceResolution',patch_id='new.panel',resolution=[6,7]),
                    dict(type='SetSurfaceMaterialRole',patch_id='new.panel',material_role='glass'),
                    dict(type='SetSurfaceMirror',patch_id='new.panel',enabled=True),
                    dict(type='AddSurfaceSupport',patch_id='new.panel',axis='u',position=.03)]:
        old=(root/'generated/surface_graph.json').read_bytes();apply(s,command);new=(root/'generated/surface_graph.json').read_bytes()
        s.undo(expected_revision=s.revision);assert (root/'generated/surface_graph.json').read_bytes()==old
        s.redo(expected_revision=s.revision);assert (root/'generated/surface_graph.json').read_bytes()==new
    assert graph(root)['patches'][-1]['id']=='new.panel'
    apply(s,dict(type='RemoveSurfaceSupport',patch_id='new.panel',axis='u',position=.03))
    apply(s,dict(type='DeleteSurfacePatch',patch_id='new.panel'),dict(type='DeleteSurfaceNode',node_id='new.sample'))
    assert graph(root)==before


@pytest.mark.parametrize('case',['unresolved','cycle','unsupported','parameter','nan','mirror','dimension'])
def test_invalid_transactions_are_atomic(root,case):
    s=AuthoringSession(root);before=s.revision
    c={'unresolved':dict(type='SetSurfaceBoundary',node_id='sample.a',boundary='left',source='missing'),
       'cycle':dict(type='SetSurfaceBoundary',node_id='sample.a',boundary='left',source='sample.a'),
       'unsupported':dict(type='SetSurfaceOperation',node_id='sample.a',op='python'),
       'parameter':dict(type='SetSurfaceParameter',node_id='sample.a',parameter='corner_tolerance',value=-1),
       'nan':dict(type='SetSurfaceParameter',node_id='bottom.a',parameter='points',value=[[0,0,0],[float('nan'),1,0]]),
       'mirror':dict(type='SetSurfaceMirror',patch_id='panel.a',enabled='yes'),
       'dimension':dict(type='SetSurfaceBoundary',node_id='sample.a',boundary='left',source='sample.b')}[case]
    with pytest.raises(ReconError):apply(s,c)
    assert s.revision==before


def test_orientation_corner_gap_and_fix_roundtrip(root):
    s=AuthoringSession(root)
    c=dict(type='ReverseSurfaceBoundary',node_id='sample.a',boundary='left')
    apply(s,c);r=evaluate(Workspace(root))
    assert r['status']=='FAIL' and not r['patches']
    assert r['corners']['sample.a'][0]['gap_m']==1
    apply(s,c);assert evaluate(Workspace(root))['status']=='PASS'
    s.undo(expected_revision=s.revision);assert evaluate(Workspace(root))['status']=='FAIL'
    s.redo(expected_revision=s.revision);assert evaluate(Workspace(root))['status']=='PASS'


def test_discontinuous_declared_boundary_and_degenerate_mesh(root):
    w=Workspace(root);g=graph(root)
    # Intentionally declare two distant edges: connectivity is never guessed from proximity.
    g['adjacency'][0]['edge_b']='right'
    r=evaluate(w,config=g);assert r['status']=='FAIL' and r['adjacency'][0]['max_gap_m']==1
    node=next(n for n in g['nodes'] if n['id']=='sample.a');node.update(op='bilinear_patch',parameters={'points':[[0,0,0]]*4},dependencies=[])
    r=evaluate(w,config=g);assert r['status']=='FAIL'
    assert 'Zero-area triangle' in r['patches'][0]['issues']
    g=graph(root);g['patches'][0]['settings']['normal']=[0,0,-1]
    assert evaluate(w,config=g)['patches'][0]['status']=='FAIL'


def test_headless_evaluation_gate_has_no_graph_or_cache_bypass(root):
    w=Workspace(root);g=graph(root);cache=PreviewCache();evaluate(w,cache=cache)
    with pytest.raises(BlockedError):Graph(g)
    s=AuthoringSession(root)
    apply(s,dict(type='MoveWorldLandmark',world_entity_id='roof_corner',point=[0,.5,1.01]))
    assert inspect(Workspace(root))['evaluation_allowed'] is False
    with pytest.raises(BlockedError):evaluate(Workspace(root),config=g,cache=cache)
    with pytest.raises(ConflictError):evaluate(w,cache=cache)
    s.undo(expected_revision=s.revision);assert evaluate(Workspace(root),cache=cache)['status']=='PASS'
    apply(s,dict(type='SetSourceDisposition',decision='INCONSISTENT_SOURCE',reviewer='Tester',notes=['Synthetic rejection']))
    with pytest.raises(BlockedError):evaluate(Workspace(root),cache=cache)


def test_incremental_cache_dependency_and_revision_identity(root):
    cache=PreviewCache();s=AuthoringSession(root)
    a=evaluate(Workspace(root),cache=cache);b=evaluate(Workspace(root),cache=cache)
    assert b['evaluated_nodes']==[] and b['sampled_patches']==[]
    apply(s,dict(type='SetSurfaceResolution',patch_id='panel.a',resolution=[4,4]))
    c=evaluate(Workspace(root),cache=cache)
    assert c['evaluated_nodes']==[] and c['sampled_patches']==['panel.a'] and c['revision']!=a['revision']
    apply(s,dict(type='SetSurfaceParameter',node_id='bottom.a',parameter='points',value=[[0,0,0],[.5,-.05,0],[1,0,0]]))
    d=evaluate(Workspace(root),cache=cache)
    assert d['evaluated_nodes']==['bottom.a','sample.a'] and d['sampled_patches']==['panel.a']
    assert cache.metrics()['mesh_bytes']<=cache.metrics()['mesh_limit_bytes']


def test_transient_invalid_graph_is_reported_without_becoming_canonical(root):
    from vehiclerecon.surfaces.preview import validate_graph
    g=graph(root);g['nodes'][-1]['dependencies'].append('missing')
    assert validate_graph(Workspace(root),g)[0]['status']=='FAIL'
    assert Workspace(root).documents['surface_graph']!=g
