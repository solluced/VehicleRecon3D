"""Dense calibrated edit followed by explicit residual/scene refresh, private fixture only."""
import cProfile,json,pstats,subprocess,sys,time,uuid
from pathlib import Path
from fastapi.testclient import TestClient
from vehiclerecon_studio.app import create_app
from vehiclerecon_studio.security import Config
repo=Path(__file__).resolve().parents[3];root=repo/f'build/studio04-calibrated-profile-{time.time_ns()}/projects'
subprocess.run([sys.executable,str(repo/'studio/backend/tests/prepare_multiview.py'),str(root),'--performance'],check=True,capture_output=True)
config=Config((root,),9173);app=create_app(config);profiles={}
for name in ('mutate','analysis'):
    original=getattr(app.state.registry,name);profile=cProfile.Profile();profiles[name]=profile
    def wrapper(*args,_original=original,_profile=profile,**kw):
        _profile.enable()
        try:return _original(*args,**kw)
        finally:_profile.disable()
    setattr(app.state.registry,name,wrapper)
with TestClient(app,base_url=config.origin) as c:
    auth=c.post('/api/v1/session/bootstrap',json={'secret':config.bootstrap},headers={'Origin':config.origin}).json()
    h={'Origin':config.origin,'X-CSRF-Token':auth['csrf'],'X-Studio-Tab':uuid.uuid4().hex}
    ident=next(p['id'] for p in c.get('/api/v1/projects').json() if p['project']['asset_name']=='multiview_performance');base='/api/v1/projects/'+ident
    snap=c.get(base,headers=h).json();rev=snap['revision'];lease=c.post(base+'/leases',json={'expected_revision':rev},headers={**h,'If-Match':rev}).json()['lease_id']
    response=c.post(base+'/transactions',json={'expected_revision':rev,'lease_id':lease,'response_format':'delta',
        'commands':[{'type':'MoveWorldLandmark','world_entity_id':'cage_landmark_0','point':[-.79,.45,.8]}]},headers={**h,'If-Match':rev,'Idempotency-Key':uuid.uuid4().hex})
    if response.status_code!=200:raise RuntimeError(response.text)
    analysis=c.get(base+'/analysis',headers=h)
    if analysis.status_code!=200:raise RuntimeError(analysis.text)
report={}
predicates={'workspace_loads':lambda f,n:f.endswith('authoring/workspace.py') and n=='__init__',
    'schema_validation':lambda f,n:f.endswith('core/project.py') and n=='validate','semantic_validation':lambda f,n:f.endswith('contracts.py') and n=='semantic_check',
    'snapshot_generation':lambda f,n:f.endswith('vehiclerecon_studio/workspace.py') and n=='snapshot','revision_hashing':lambda f,n:f.endswith('revisions.py') and n=='revision',
    'serialization':lambda f,n:'/json/' in f and n in ('dumps','encode','iterencode'),'writes':lambda f,n:f.endswith('transactions.py') and n=='atomic_write',
    'fsync':lambda f,n:'fsync' in n,'residual_recomputation':lambda f,n:f.endswith('projection.py') and n=='residual_report'}
for label,prof in profiles.items():
    stats=pstats.Stats(prof);phases={}
    for name,predicate in predicates.items():
        rows=[v for (f,line,n),v in stats.stats.items() if predicate(f.replace('\\','/'),n)]
        phases[name]={'calls':sum(v[1] for v in rows),'self_seconds':sum(v[2] for v in rows),'cumulative_seconds':sum(v[3] for v in rows)}
    report[label]={'total_profiled_seconds':stats.total_tt,'phases':phases}
out={'status':'PASS','entities':5000,'bound_residual_rows':len(analysis.json()['residuals']['rows']),'edit_delta_bytes':len(response.content),
    'analysis_response_bytes':len(analysis.content),'profiles':report,'note':'Cumulative phase times overlap. Mutation and requested analysis are separately instrumented; HTTP response construction is measured in the source-edit retention profile.'}
(repo/'build/studio04-calibrated-edit-profile.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,indent=2))
