"""Authenticated dense-save/CV retention probe. Writes private build fixtures only."""
import argparse,cProfile,gc,json,os,pstats,subprocess,sys,time,uuid
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--label',default='final');p.add_argument('--edits',type=int,default=100)
p.add_argument('--package-root',type=Path);p.add_argument('--cv',action='store_true');p.add_argument('--delta',action='store_true')
a=p.parse_args()
if not 1<=a.edits<=1000 or not a.label.replace('-','').isalnum():p.error('Invalid edits/label')
repo=Path(__file__).resolve().parents[3]
if a.package_root:sys.path.insert(0,str(a.package_root.resolve(strict=True)))
from fastapi.testclient import TestClient
from vehiclerecon_studio.security import Config
from vehiclerecon_studio.app import create_app
root=repo/f'build/studio03-retention-{a.label}-{time.time_ns()}/projects'
subprocess.run([sys.executable,str(repo/'studio/backend/tests/prepare_browser.py'),str(root),'--performance'],check=True,capture_output=True)
config=Config((root,),9173);app=create_app(config)
prof=cProfile.Profile();original=app.state.registry.mutate;first=[True]
def measured(*args,**kw):
    if not first[0]:return original(*args,**kw)
    first[0]=False;prof.enable()
    try:return original(*args,**kw)
    finally:prof.disable()
app.state.registry.mutate=measured
def rss(peak=False):return int(subprocess.check_output([sys.executable,str(repo/'studio/backend/tests/process_memory.py'),str(os.getpid()),*(['--peak'] if peak else [])],text=True))
with TestClient(app,base_url=config.origin) as c:
    token=c.post('/api/v1/session/bootstrap',json={'secret':config.bootstrap},headers={'Origin':config.origin}).json()
    h={'Origin':config.origin,'X-CSRF-Token':token['csrf'],'X-Studio-Tab':uuid.uuid4().hex}
    ident=next(x['id'] for x in c.get('/api/v1/projects').json() if x['project']['asset_name']=='performance');base='/api/v1/projects/'+ident
    s=c.get(base,headers=h).json();rev=s['revision'];ref=s['references'][0]['id']
    lease=c.post(base+'/leases',json={'expected_revision':rev},headers={**h,'If-Match':rev}).json()['lease_id']
    def post(op,**body):
        r=c.post(base+'/'+op,json={'expected_revision':rev,'lease_id':lease,**body},headers={**h,'If-Match':rev,'Idempotency-Key':uuid.uuid4().hex})
        if r.status_code not in (200,202):raise RuntimeError(r.text)
        return r
    def proposal(threshold):
        j=post('cv-jobs',request={'provider_id':'opencv','capability':'trace_contour','reference_id':ref,'view':'side',
            'parameters':{'roi':[290,440,650,610],'threshold':threshold,'tolerance':2}}).json()
        while j['activity']!='FINISHED':
            time.sleep(.01);j=c.get(base+'/cv-jobs/'+j['job_id'],headers=h).json()
        if j['result']!='SUCCEEDED':raise RuntimeError(str(j))
        return c.get(base+'/cv-proposals/'+j['proposal_id'],headers=h).json()
    baseline=rss();samples=[];times=[];counts={'accepted':0,'rejected':0,'left_active_then_stale':0};first_rejected=None
    for i in range(a.edits):
        cv=proposal(60+i) if a.cv else None
        if cv and i%3==1 and i%10!=9:
            post('cv-proposals/'+cv['proposal_id']+'/reject',component_ids=[x['id'] for x in cv['components']])
            counts['rejected']+=1;first_rejected=first_rejected or cv['proposal_id']
        start=time.perf_counter()
        if cv and i%10==9 and cv['components']:
            component=cv['components'][0]
            response=post('cv-proposals/'+cv['proposal_id']+'/accept',proposal_revision=cv['proposal_revision'],
                component_ids=[component['id']],semantic_roles={component['id']:'roof'},response_format='delta' if a.delta else 'full')
            counts['accepted']+=1
        else:
            response=post('transactions',commands=[{'type':'SetObservationProperties','observation_id':'perf_0','values':{'uncertainty_px':2+i}}],
                **({'response_format':'delta'} if a.delta else {}))
            if cv and i%3!=1:
                stale=c.get(base+'/cv-proposals/'+cv['proposal_id'],headers=h).json()
                if stale['status']!='STALE':raise RuntimeError('Proposal did not stale after canonical edit')
                counts['left_active_then_stale']+=1
        rev=response.json()['revision'];times.append(time.perf_counter()-start)
        if (i+1)%10==0 or i==a.edits-1:
            samples.append({'edits':i+1,'rss_bytes':rss()});print(a.label,i+1,round(times[-1],3),'s',flush=True)
    retention=app.state.registry.cv.metrics() if a.cv else {}
    evicted=c.get(base+'/cv-proposals/'+first_rejected,headers=h).status_code==404 if first_rejected else None
    active_proposal=proposal(215) if a.cv else None
    time.sleep(1);gc.collect();after=rss();reg=app.state.registry;session=next(iter(reg.sessions.values()))
    stats=pstats.Stats(prof);phases={}
    predicates={'schema_validation':lambda f,n:f.endswith('core/project.py') and n=='validate',
        'semantic_validation':lambda f,n:f.endswith('contracts.py') and n=='semantic_check',
        'json_serialization':lambda f,n:'/json/' in f and n in ('dumps','encode','iterencode'),
        'revision_hashing':lambda f,n:f.endswith('revisions.py') and n=='revision',
        'transaction_commit':lambda f,n:f.endswith('transactions.py') and n=='commit',
        'snapshot_refresh':lambda f,n:'vehiclerecon_studio' in f and n=='snapshot','fsync':lambda f,n:'fsync' in n}
    for phase,fn in predicates.items():
        values=[v for (f,_,n),v in stats.stats.items() if fn(f.replace('\\','/'),n)]
        phases[phase]={'calls':sum(v[1] for v in values),'self_seconds':sum(v[2] for v in values),'cumulative_seconds':sum(v[3] for v in values)}
    hot=sorted([{'file':f.replace('\\','/').split('/')[-1],'line':line,'function':fn,'calls':v[1],'self_seconds':v[2],
        'cumulative_seconds':v[3]} for (f,line,fn),v in stats.stats.items()],key=lambda v:-v['cumulative_seconds'])[:50]
    result={'status':'PASS','label':a.label,'canonical_edits':a.edits,'entities_initial':5000,'response_format':'delta' if a.delta else 'full',
        'timings_seconds':times,'p95_seconds':sorted(times)[min(len(times)-1,int(len(times)*.95))],
        'rss_baseline_bytes':baseline,'rss_peak_sampled_bytes':max([baseline]+[s['rss_bytes'] for s in samples]),
        'rss_peak_process_bytes':rss(True),'rss_after_gc_bytes':after,'rss_samples':samples,'idle_seconds':1,
        'history_bytes':session.history_retained_bytes,'undo_entries':len(session.undo_stack),
        'idempotency_bytes':reg.requests.retained_bytes,'idempotency_entries':len(reg.requests),
        'last_response_payload_bytes':len(response.content),'cv':retention,'proposal_states_exercised':counts,
        'active_at_end':active_proposal is not None,'first_rejected_evicted':evicted,
        'profile_total_seconds':stats.total_tt,'profile_phases':phases,'profile':hot,
        'note':'First canonical edit instrumented; cumulative phases overlap. Later timings include API readback of STALE state when exercised; browser benchmark is separate.'}
    (repo/f'build/studio03-retention-{a.label}.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('profile','timings_seconds','rss_samples')},indent=2))
