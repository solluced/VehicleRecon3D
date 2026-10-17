"""Project-scoped read-only adapters for shared v2 and verified legacy evidence."""
import json
from vehiclerecon.authoring.consistency import analyze,heat,summarize,scene,wheelbase,HEAT_POLICY
from vehiclerecon.authoring.reviews import subject,review_status,PATHS
from vehiclerecon.core.errors import ReconError
from vehiclerecon.core.manifest import digest_file
from vehiclerecon.core.project import read_json


def framing(calibration):
    return {v:{'crop':d.get('crop'),'calibrated':all(k in d for k in ('origin','u_basis','v_basis')),
               'rectification':'ACTIVE' if 'rectification' in d else 'NONE','coordinate_system':'RAW SOURCE PIXELS'}
            for v,d in calibration.get('views',{}).items()}


def v2_analysis(w):
    cal=w.documents.get('calibration',{});cage=w.documents.get('cage',{'landmarks':{},'curves':[]})
    try:result=analyze(cal,cage)
    except (ReconError,KeyError,TypeError,ValueError) as exc:
        result={'residuals':{'status':'BLOCKED','rows':[],'coverage':{},'summary':{}},'heat_policy':HEAT_POLICY,'coverage':[],
                'groups':summarize([]),'correspondences':cal.get('correspondences',[]),'world_landmarks':cage.get('landmarks',{}),
                'scene':{'landmarks':cage.get('landmarks',{}),'controls':[],'curves':[],'axes':{'X':'longitudinal','Y':'lateral','Z':'up'},'units':'m'},
                'policy':cal.get('authoring_policy'),'ratios':{'status':'NOT ENOUGH DATA','rows':[]},
                'wheelbase':wheelbase(cal,cal.get('datums',{}).get('measurements',[])),
                'unavailable_reason':'Calibrated projection is incomplete: '+str(exc)[:200]}
    reviews={}
    for kind in ('source','cage'):
        try:identity=subject(w,kind);issue=None
        except (ReconError,KeyError,OSError,TypeError,ValueError) as exc:identity=None;issue=str(exc)[:200]
        reviews[kind]={'subject':identity,'status':review_status(w,kind),'issue':issue,
                       'record':json.loads(w.files[PATHS[kind]]) if PATHS[kind] in w.files else None}
    candidates=[]
    for path,raw in w.files.items():
        if path.startswith('validation/rectification_candidates/'):
            c=json.loads(raw);candidates.append({'id':c['id'],'status':c['status'],'view':c['view']})
    return {**result,'views':framing(cal),'reviews':reviews,'rectification_candidates':candidates,'read_only':False,
            'revision':w.revision,'dimensions':w.documents['project']['dimensions'],
            'measurements':cal.get('datums',{}).get('measurements',[]),
            'input_identities':{k:digest_file(w.project.path(p,exists=True)) for k,p in w.documents['project']['references'].items()}}


def legacy_analysis(project,guard):
    """Recognized historical reports only; never migrate v1 or activate candidates."""
    root=project.root;cal=read_json(project.path(project.data['generated']['calibration'],exists=True))
    cage=read_json(project.path(project.data['generated']['cage'],exists=True))
    result={'read_only':True,'legacy':True,'views':framing(cal),'scene':scene(cal,cage),'residuals':{'rows':[],'status':'UNKNOWN','summary':{}},
            'coverage':[],'heat_policy':HEAT_POLICY,'groups':summarize([]),'correspondences':[],
            'world_landmarks':cage.get('landmarks',{}),'policy':None,'ratios':{'status':'NOT ENOUGH DATA','rows':[]},'reviews':{},
            'wheelbase':wheelbase(cal,[]),'rectification_candidates':[],'dimensions':project.data['dimensions'],
            'input_identities':{k:digest_file(project.path(p,exists=True)) for k,p in project.data['references'].items()}}
    def report(name):
        path=guard(root,root/'validation'/name)
        return read_json(path) if path.is_file() and path.stat().st_size<8*1024*1024 else None
    stored=report('cage_residuals.json')
    if stored:
        checks={'calibration_sha256':project.data['generated']['calibration'],'cage_sha256':project.data['generated']['cage'],
                'reference_observations_sha256':'validation/correction_reference_landmarks.json'}
        current=all(stored.get(k)==digest_file(guard(root,root/p)) for k,p in checks.items())
        current=current and stored.get('source_sha256')==digest_file(project.path(project.data['references']['multiview'],exists=True))
        result['legacy_evidence_current']=current
        if current:
            rows=[]
            for i,r in enumerate(stored.get('rows',stored.get('checks',[]))):
                allowed=r.get('allowed_px',r.get('uncertainty_px',r.get('tolerance_px')))
                if allowed is None:continue
                rows.append(heat({'id':'legacy_'+str(i),'observation_id':'legacy_obs_'+str(i),'world_entity_id':r['landmark'],
                    'semantic_role':r['landmark'],'view':r['view'],'observed_pixel':r['reference_pixel'],'projected_pixel':r['projected_pixel'],
                    'world':r['world'],'residual_px':r['residual_px'],'allowed_tolerance_px':allowed,
                    'critical':r.get('critical',True),'required':r.get('critical',True),'status':'PASS' if r['residual_px']<=allowed else 'FAIL','inferred':False}))
            result.update(residuals={'rows':rows,'status':stored['status'],'summary':stored['summary']},groups=summarize(rows))
            result['scene']['landmarks']={r['world_entity_id']:r['world'] for r in rows}
            result['world_landmarks']=result['scene']['landmarks']
            result['legacy_summary']=stored['summary']
            ratios=report('view_longitudinal_ratios.json')
            if ratios and ratios.get('source_sha256')==stored['source_sha256']:result['legacy_ratios']=ratios
    reconciliation=report('reference_reconciliation_report.json')
    if reconciliation:
        result['source_condition']='INCONSISTENT_SOURCE' if reconciliation.get('status')=='REFERENCE_SOURCE_INCONSISTENT' else reconciliation.get('status')
    candidate=report('rectification_candidate.json');magnitude=report('rectification_magnitude.json')
    if candidate:
        result['rectification_candidates']=[{'status':candidate['status'],'view':candidate.get('affected_view'),'rejection':candidate.get('rejection'),'magnitude':magnitude}]
    stock=cal.get('datums',{}).get('stock_body_dimensions_m',{}).get('wheelbase')
    if stock is not None:
        result['wheelbase'].update(authoritative_wheelbase_m=stock,difference_m=result['wheelbase']['world_wheelbase_m']-stock,
                                   authority={'provenance':'Existing documented stock dimensions; not a replacement drift envelope'})
    return result
