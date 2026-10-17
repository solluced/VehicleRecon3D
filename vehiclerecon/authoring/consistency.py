"""Shared diagnostic presentation derived from declared evidence, never gates."""
import math
from .contracts import observations, VIEWS, point_value
from .projection import residual_report, sample_cage
from ..reference.transforms import CalibrationTransform


HEAT_POLICY={'metric':'residual / declared tolerance','near_ratio':.8,'fail_ratio':1.,
             'acceptance':'Each critical/required residual is checked individually; colors never replace gates.'}


def heat(row):
    ratio=row['residual_px']/row['allowed_tolerance_px'] if row.get('residual_px') is not None else None
    return {**row,'ratio':ratio,'heat':'UNKNOWN' if ratio is None else 'FAIL' if ratio>HEAT_POLICY['fail_ratio'] else 'NEAR' if ratio>=HEAT_POLICY['near_ratio'] else 'PASS'}


def group(role):
    value=role.lower()
    if 'axle' in value or 'wheel' in value:return 'AXLES'
    if 'pillar' in value:return 'PILLARS'
    if 'door' in value:return 'DOORS'
    if any(v in value for v in ('roof','glass','greenhouse','windshield','window')):return 'GREENHOUSE'
    if any(v in value for v in ('hood','trunk','bumper','belt','body','envelope')):return 'ENVELOPE'
    return 'SECONDARY FEATURES'


def summarize(rows):
    result=[]
    for name in ('AXLES','ENVELOPE','GREENHOUSE','PILLARS','DOORS','SECONDARY FEATURES'):
        selected=[r for r in rows if group(r['semantic_role'])==name]
        state='NOT ENOUGH DATA' if not selected or any(r['heat']=='UNKNOWN' for r in selected) else 'FAIL' if any(r['heat']=='FAIL' for r in selected) else 'WARNING' if any(r['heat']=='NEAR' for r in selected) else 'PASS'
        result.append({'group':name,'state':state,'tolerance_status':'FAIL' if any(r['status']=='FAIL' for r in selected) else 'PASS' if selected and all(r['status']=='PASS' for r in selected) else 'UNKNOWN',
                       'count':len(selected),'critical_failures':sum(r.get('critical',False) and r['heat']=='FAIL' for r in selected)})
    return result


def wheelbase(calibration,measurements):
    wheels=calibration.get('wheel_geometry',{});axles={a['id']:a for a in wheels.get('axles',[])}
    current=abs(axles['rear']['x']-axles['front']['x']) if {'front','rear'}<=axles.keys() else None
    authority=next((m for m in measurements if 'wheelbase' in m.get('meaning','').lower() and m.get('value') is not None and m['unit'] in ('m','mm') and m['provenance']['type'] in ('official','measured')),None)
    official=authority['value']*(.001 if authority['unit']=='mm' else 1) if authority else None
    return {'front_axle':axles.get('front'),'rear_axle':axles.get('rear'),'world_wheelbase_m':current,
            'authoritative_wheelbase_m':official,'authority':authority,'difference_m':current-official if current is not None and official is not None else None}


def longitudinal_ratios(calibration,rows):
    axles={a['id']:a for a in calibration.get('wheel_geometry',{}).get('axles',[])}
    if not {'front','rear'}<=axles.keys():return {'status':'NOT ENOUGH DATA','rows':[],'reason':'Shared front/rear axle datums required'}
    transform=CalibrationTransform(calibration);anchors={}
    for view in ('side','top'):
        anchors[view]=[transform.world_to_pixel(view,axles[k]['x'],0,axles[k]['z'])[0] for k in ('front','rear')]
        if abs(anchors[view][1]-anchors[view][0])<1e-9:
            return {'status':'NOT ENOUGH DATA','rows':[],'reason':'Longitudinal pixel axis is not independently resolved'}
    entities={}
    for r in rows:
        if r['view'] not in anchors or r['observed_pixel'] is None:continue
        a,b=anchors[r['view']];key=(r['world_entity_id'],r.get('point_id'),r.get('side',1))
        entities.setdefault(key,{'entity_id':r['world_entity_id'],'point_id':r.get('point_id'),'semantic_role':r['semantic_role'],'views':{}})['views'][r['view']]={
            'ratio':(r['observed_pixel'][0]-a)/(b-a),'tolerance_ratio':r['allowed_tolerance_px']/abs(b-a)}
    result=[]
    for e in entities.values():
        both={'side','top'}<=e['views'].keys();delta=e['views']['top']['ratio']-e['views']['side']['ratio'] if both else None
        limit=sum(v['tolerance_ratio'] for v in e['views'].values())
        result.append({**e,'delta':delta,'declared_tolerance_ratio':limit,'status':'UNKNOWN' if not both else 'FAIL' if abs(delta)>limit else 'PASS'})
    return {'status':'FAIL' if any(r['status']=='FAIL' for r in result) else 'PASS' if result and all(r['status']=='PASS' for r in result) else 'NOT ENOUGH DATA',
            'anchors':anchors,'rows':result,'policy':'Original source u normalized between shared projected axle datums; combined declared pixel tolerances. Diagnostic only; no calibration mutation.'}


def scene(calibration,cage):
    controls=[];mirrors=[]
    for curve in cage.get('curves',[]):
        for ident,p in zip(curve.get('point_ids',[]),curve['points']):
            controls.append({'id':ident,'entity_id':curve['id'],'landmark':p.get('landmark') if isinstance(p,dict) else None,'xyz':list(point_value(cage,p)),'semantic_role':curve['role']})
            if curve.get('symmetry'):
                xyz=point_value(cage,p)
                for side,sign in cage.get('sides',[]):
                    if sign!=1:mirrors.append({'id':ident,'entity_id':curve['id'],'side':side,'xyz':[xyz[0],sign*xyz[1],xyz[2]],'display_only':True})
    wheels=[]
    geometry=calibration.get('wheel_geometry',{})
    for axle in geometry.get('axles',[]):
        for side,sign in cage.get('sides',[['L',-1],['R',1]]):
            xyz=[axle['x'],sign*axle['track_m']/2,axle['z']];radius=geometry['radius_m']
            wheels.append({'id':axle['id']+'_'+side,'xyz':xyz,'world_samples':[[xyz[0]+radius*math.cos(i*math.tau/64),xyz[1],xyz[2]+radius*math.sin(i*math.tau/64)] for i in range(65)]})
    return {'landmarks':cage.get('landmarks',{}),'controls':controls,'mirrored_controls':mirrors,'wheels':wheels,
            'curves':sample_cage(calibration,cage) if calibration.get('wheel_geometry') else [],
            'wheel_geometry':calibration.get('wheel_geometry'),'symmetry':{'plane':'Y=0','declared':any(c.get('symmetry') for c in cage.get('curves',[])),
                'sides':cage.get('sides',[]),'editing':'Display only; no implicit mirrored commands'},
            'axes':{'X':'longitudinal','Y':'lateral','Z':'up'},'units':'m'}


def analyze(calibration,cage):
    report=residual_report(calibration,cage);obs=observations(calibration);coverage=[]
    links={l['id']:l for l in calibration['correspondences']}
    rows=[heat({**r,'critical':r['id'] in calibration['authoring_policy']['critical_correspondence_ids'],
                'side':links[r['id']].get('side',1),'binding_type':links[r['id']]['binding_type'],
                'observation_point_id':links[r['id']].get('observation_point_id'),
                'inferred':obs[r['observation_id']]['visibility']=='inferred' or not obs[r['observation_id']]['measured']}) for r in report['rows']]
    entities={(r['world_entity_id'],r.get('point_id') or '') for r in rows}|{(name,'') for name in cage.get('landmarks',{})}
    for entity,point_id in sorted(entities):
        matching=[r for r in rows if r['world_entity_id']==entity and (r.get('point_id') or '')==point_id]
        coverage.append({'entity_id':entity,'point_id':point_id or None,'views':{v:sum(r['view']==v and r['observed_pixel'] is not None for r in matching) for v in VIEWS},
                         'semantic_roles':sorted({r['semantic_role'] for r in matching})})
    return {'residuals':{**report,'rows':rows},'heat_policy':HEAT_POLICY,'coverage':coverage,'groups':summarize(rows),
            'correspondences':calibration['correspondences'],'policy':calibration['authoring_policy'],
            'world_landmarks':cage.get('landmarks',{}),'scene':scene(calibration,cage),
            'wheelbase':wheelbase(calibration,calibration.get('datums',{}).get('measurements',[])),
            'ratios':longitudinal_ratios(calibration,rows),'unbound_observations':sorted(set(obs)-{r['observation_id'] for r in rows})}
