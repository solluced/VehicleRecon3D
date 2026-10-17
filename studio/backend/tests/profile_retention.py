"""Release profiling through the authenticated API on private dense fixtures."""
import cProfile,gc,json,os,pstats,subprocess,sys,time,uuid
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--label',default='final')
parser.add_argument('--edits',type=int,default=100)
parser.add_argument('--package-root',type=Path)
args=parser.parse_args()
if not 1<=args.edits<=10000:parser.error('edits must be 1..10000')
label=args.label
if not label.replace('-','').isalnum():parser.error('label must be alphanumeric/hyphen')
repo=Path(__file__).resolve().parents[3]
if args.package_root:sys.path.insert(0,str(args.package_root.resolve(strict=True)))
from fastapi.testclient import TestClient
from vehiclerecon_studio.security import Config
from vehiclerecon_studio.app import create_app

count=args.edits;root=repo/f'build/studio02-profile-{label}-{int(time.time())}/projects'
subprocess.run([sys.executable,str(repo/'studio/backend/tests/prepare_browser.py'),str(root),'--performance'],check=True,capture_output=True)
config=Config((root,),9173);app=create_app(config);client=TestClient(app,base_url=config.origin)
prof=cProfile.Profile();original=app.state.registry.mutate;profiled=[False]
def measure(*args,**kwargs):
    if profiled[0]:return original(*args,**kwargs)
    profiled[0]=True;prof.enable()
    try:return original(*args,**kwargs)
    finally:prof.disable()
app.state.registry.mutate=measure
token=client.post('/api/v1/session/bootstrap',json={'secret':config.bootstrap},headers={'Origin':config.origin}).json()
h={'Origin':config.origin,'X-CSRF-Token':token['csrf'],'X-Studio-Tab':uuid.uuid4().hex}
ident=next(p['id'] for p in client.get('/api/v1/projects').json() if p['project']['asset_name']=='performance')
snap=client.get('/api/v1/projects/'+ident,headers=h).json();rev=snap['revision']
lease=client.post(f'/api/v1/projects/{ident}/leases',json={'expected_revision':rev},headers={**h,'If-Match':rev}).json()['lease_id']
def rss():return int(subprocess.check_output([sys.executable,str(repo/'studio/backend/tests/process_memory.py'),str(os.getpid())],text=True))
baseline=rss();samples=[];times=[]
for i in range(count):
    start=time.perf_counter();response=client.post(f'/api/v1/projects/{ident}/transactions',json={'expected_revision':rev,'lease_id':lease,
        'commands':[{'type':'SetObservationProperties','observation_id':'perf_0','values':{'uncertainty_px':2+i}}]},
        headers={**h,'If-Match':rev,'Idempotency-Key':uuid.uuid4().hex})
    if response.status_code!=200:raise RuntimeError(response.text)
    rev=response.json()['revision'];times.append(time.perf_counter()-start)
    if (i+1)%10==0 or i==count-1:
        samples.append({'edits':i+1,'rss_bytes':rss()});print(label,i+1,round(times[-1],3),'s',flush=True)
peak=max([baseline]+[s['rss_bytes'] for s in samples]);time.sleep(1);gc.collect();after=rss()
stats=pstats.Stats(prof);hot=sorted([{'file':Path(f.replace('\\','/')).name,'line':line,'function':func,'calls':v[1],'self_seconds':v[2],'cumulative_seconds':v[3]} for (f,line,func),v in stats.stats.items()],key=lambda r:r['cumulative_seconds'],reverse=True)[:45]
reg=app.state.registry;session=reg.sessions[(ident,next(iter(reg.sessions))[1])]
phases={}
for name,fn in {'json_serialization':lambda f,n:Path(f.replace('\\','/')).name in ('encoder.py','__init__.py') and 'json' in f and n in ('dumps','encode','iterencode'),
    'schema_validation':lambda f,n:f.replace('\\','/').endswith('core/project.py') and n=='validate',
    'semantic_validation':lambda f,n:Path(f.replace('\\','/')).name=='contracts.py' and n=='semantic_check',
    'revision_hashing':lambda f,n:Path(f.replace('\\','/')).name=='revisions.py' and n=='revision',
    'transaction_commit':lambda f,n:Path(f.replace('\\','/')).name=='transactions.py' and n=='commit',
    'fsync':lambda f,n:'fsync' in n,
    'snapshot_refresh':lambda f,n:'vehiclerecon_studio' in f and n=='snapshot'}.items():
    matching=[v for (f,line,n),v in stats.stats.items() if fn(f.replace('/','\\'),n)]
    phases[name]={'calls':sum(v[1] for v in matching),'self_seconds':sum(v[2] for v in matching),'cumulative_seconds':sum(v[3] for v in matching)}
from vehiclerecon.core import schema_dispatch
peak_process=int(subprocess.check_output([sys.executable,str(repo/'studio/backend/tests/process_memory.py'),str(os.getpid()),'--peak'],text=True))
result={'label':label,'canonical_edits':count,'entities':5000,'timing_seconds':times,'p95_seconds':sorted(times)[int(len(times)*.95)],
    'rss_baseline_bytes':baseline,'rss_peak_sampled_bytes':peak,'rss_after_gc_bytes':after,'rss_samples':samples,
    'undo_entries':len(session.undo_stack),'idempotency_entries':len(reg.requests),'profile':hot,'profile_total_seconds':stats.total_tt,
    'history_bytes':getattr(session,'history_retained_bytes',None),'idempotency_bytes':getattr(reg.requests,'retained_bytes',None),
    'rss_peak_process_bytes':peak_process,'idle_seconds':1,'profile_phases':phases,'last_response_payload_bytes':len(response.content),
    'schema_cache_entries':len(schema_dispatch._valid),'schema_cache_bytes':schema_dispatch._bytes,
    'phase_note':'First request cProfile timings overlap and include instrumentation; subsequent timing samples are unprofiled. JSON includes canonical snapshot; no image decode/cache in this edit window.'}
Path(repo/f'build/studio02-profile-{label}.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('profile','timing_seconds','rss_samples')},indent=2))
