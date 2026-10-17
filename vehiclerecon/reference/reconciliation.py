"""Core-only candidate evaluation. No images, frontend math or canonical writes."""
import copy,math
from .rectification import PiecewiseMonotonicAxisWarp,AxisRectification
from .transforms import CalibrationTransform
from ..core.errors import SchemaError,ConflictError,ReferenceError,ReconError
from ..core.manifest import digest_data,digest_file
from ..core.project import validate
from ..authoring.contracts import observations,observed_pixel,world_binding

ALGORITHM='PiecewiseMonotonicAxisWarp/1'
SCALE_EPSILON=1e-12

def rms(values):return math.sqrt(sum(v*v for v in values)/len(values)) if values else None

def evidence(workspace,view):
    from ..authoring.projection import registered
    cal=workspace.documents['calibration'];cage=workspace.documents.get('cage',{'curves':[],'landmarks':{}})
    affine=copy.deepcopy(cal);affine['views'][view].pop('rectification',None)
    transform=CalibrationTransform(affine);current=CalibrationTransform(cal);obs=observations(cal);rows=[]
    for link in cal.get('correspondences',[]):
        o=obs[link['observation_id']]
        if o['view']!=view:continue
        pixel=observed_pixel(o,link)
        if pixel is None or not o['measured'] or o['visibility']!='observed' or not registered(cal,o):continue
        world=world_binding(cage,link)
        rows.append({'id':link['id'],'observation_id':o['id'],'semantic':o['semantic_role'],'pixel':list(pixel),
            'projected_affine':list(transform.world_to_pixel(view,*world)),
            'projected_raw':list(current.world_to_pixel(view,*world)),
            'tolerance_px':link['tolerance_policy']['allowed_px'],
            'critical':link['required'] or link['id'] in cal['authoring_policy']['critical_correspondence_ids'],'world_entity_id':link['world_entity_id'],
            'reference_id':o['reference_id'],'source_sha256':o['source_sha256'],
            'measured':True,'provenance':copy.deepcopy(o['provenance'])})
    return rows

def make_candidate(workspace,request,*,ident,creator):
    validate(request,'reconciliation_request')
    view=request['view'];cal=workspace.documents['calibration'];d=cal['views'][view]
    if d.get('source_state')=='CALIBRATION_REQUIRED':raise ReferenceError('Replacement source framing must be recalibrated before candidate generation')
    reference=request['reference_role']
    if reference not in workspace.project.data['references']:raise ReferenceError('Unknown source role')
    if reference!=d.get('reference_id','multiview'):raise ReferenceError('Choose the calibrated active source view')
    rows=[r for r in evidence(workspace,view) if r['reference_id']==reference]
    axis=0 if request['axis']=='u' else 1
    start=[d['crop'][0],d['crop'][1]];end=list(start)
    start[axis],end[axis]=request['affine_domain_px']
    equivalent_m=math.dist(CalibrationTransform(cal).pixel_to_world(view,*start),CalibrationTransform(cal).pixel_to_world(view,*end))
    return {'schema_version':2,'id':ident,'status':'DRAFT','revision':1,'view':view,
        'source_revision':workspace.revision,'base_calibration_hash':digest_data(cal),
        'source_hashes':{k:digest_file(workspace.project.path(p,exists=True)) for k,p in workspace.project.data['references'].items()},
        'crop':copy.deepcopy(d['crop']),'request':copy.deepcopy(request),'evidence':rows,
        'creator':creator,'algorithm':ALGORITHM,'wheelbase_m':equivalent_m,
        'physical_basis':'Calibrated affine domain span; equivalent source correction, not a physical change'}

def current(workspace,candidate):
    return (workspace.revision==candidate['source_revision'] and
        digest_data(workspace.documents['calibration'])==candidate['base_calibration_hash'] and
        {k:digest_file(workspace.project.path(p,exists=True)) for k,p in workspace.project.data['references'].items()}==candidate['source_hashes'] and
        workspace.documents['calibration']['views'][candidate['view']]['crop']==candidate['crop'])

def model(request):
    return {'type':'piecewise_monotonic','axis':request['axis'],'image_domain_px':request['image_domain_px'],
        'affine_domain_px':request['affine_domain_px'],'max_scale_change':request['max_scale_change'],
        'anchors':[{'image':a['image'],'world_normalized':a['world_normalized'],'semantic':a['semantic']} for a in request['anchors'] if a['role']=='FIT']}

def audit(rectification,crop,*,wheelbase_m=None,samples=257):
    """Audit even an excessive candidate without authorizing AxisRectification."""
    warp=PiecewiseMonotonicAxisWarp([a['image'] for a in rectification['anchors']],[a['world_normalized'] for a in rectification['anchors']])
    a,b=rectification['image_domain_px'];c,d=rectification['affine_domain_px'];axis=0 if rectification['axis']=='u' else 1
    if b<=a or d<=c:raise SchemaError('Image and affine domains must increase')
    lo=(crop[axis]-a)/(b-a);hi=(crop[axis+2]-a)/(b-a)
    def correction(region):
        p=warp.maximum_identity_correction(*region)
        return {**p,'maximum_correction_px':p['maximum_absolute_normalized']*(b-a),
            'maximum_equivalent_mm':p['maximum_absolute_normalized']*wheelbase_m*1000 if wheelbase_m else None,'range':list(region)}
    ext=warp.derivative_extrema(lo,hi)
    points=[]
    xs=sorted(set([lo+(hi-lo)*i/(samples-1) for i in range(samples)]+list(warp.x)+[0,1]))
    for x in xs:
        y=warp(x);q=y-x
        points.append({'x':x,'y':y,'correction':q,'correction_px':q*(b-a),'equivalent_mm':q*wheelbase_m*1000 if wheelbase_m else None,
            'derivative':warp.derivative(x),'source_px':a+x*(b-a),'target_px':c+y*(d-c),'extrapolated':x<warp.x[0] or x>warp.x[-1]})
    outside=max(0,min(hi,warp.x[0])-lo)+max(0,hi-max(lo,warp.x[-1]))
    return {'samples':points,'derivative_extrema':ext,'local_scale_range':[ext['minimum']['derivative'],ext['maximum']['derivative']],
        'between_datums':correction([0,1]),'whole_crop':correction([lo,hi]),
        'extrapolation':{'fraction':outside/(hi-lo),'fitted_support':[warp.x[0],warp.x[-1]],
            'front_range':[lo,min(0,hi)] if lo<0 else None,'rear_range':[max(1,lo),hi] if hi>1 else None,
            'policy':'Positive linear tails outside fitted support; overhangs reported separately from between-datum evidence'},
        'strictly_monotonic':True,'derivative_positive':True,'foldover':False}

def evaluate(candidate):
    request=candidate['request'];validate(request,'reconciliation_request');r=model(request);anchors=request['anchors'];fit=[a for a in anchors if a['role']=='FIT'];reasons=[]
    result={'eligible':False,'status':'EVALUATED','reasons':reasons,'model':r,'anchors':copy.deepcopy(anchors),
        'strictly_monotonic':False,'derivative_positive':False,'foldover':True,'held_out':[],'features':candidate['evidence'],
        'allowed_scale':[1-request['max_scale_change'],1+request['max_scale_change']],'scale_epsilon':SCALE_EPSILON}
    try:
        if len({a['id'] for a in anchors})!=len(anchors):raise SchemaError('Duplicate anchor ID')
        locks=[a for a in fit if a['locked']]
        if len(locks)!=2 or sorted((a['image'],a['world_normalized']) for a in locks)!=[(0,0),(1,1)]:
            raise SchemaError('Both normalized datum anchors must be exact, locked and FIT')
        plot=audit(r,candidate['crop'],wheelbase_m=candidate['wheelbase_m']);result.update(plot)
    except (ReconError,ValueError,IndexError) as exc:
        reasons.append(str(exc));return result
    lo,hi=result['local_scale_range'];limit=request['max_scale_change']
    if lo<1-limit-SCALE_EPSILON or hi>1+limit+SCALE_EPSILON:reasons.append('OUTSIDE SCALE LIMIT')
    if result['extrapolation']['fraction']>0 and not request['allow_extrapolation']:reasons.append('Extrapolation policy forbids unsupported crop regions')
    if result['extrapolation']['fraction']>.5+SCALE_EPSILON:reasons.append('More than half the source crop lies outside fitted support')
    warp=PiecewiseMonotonicAxisWarp([a['image'] for a in fit],[a['world_normalized'] for a in fit])
    a,b=r['image_domain_px'];c,d=r['affine_domain_px'];axis=0 if r['axis']=='u' else 1
    rows={e['observation_id']:e for e in candidate['evidence']};used=set();fit_ids=set();held_ids=set()
    for anchor in anchors:
        oid=anchor.get('observation_id')
        if oid:
            if oid not in rows:reasons.append('Anchor requires current measured correspondence: '+oid);continue
            row=rows[oid];sx=(row['pixel'][axis]-a)/(b-a);ty=(row['projected_affine'][axis]-c)/(d-c)
            if abs(sx-anchor['image'])>1e-9 or abs(ty-anchor['world_normalized'])>1e-9:
                reasons.append('Bound anchor coordinates do not match canonical evidence: '+oid)
            if oid in used:reasons.append('Evidence cannot be fitted and held out or counted twice: '+oid)
            used.add(oid)
            (fit_ids if anchor['role']=='FIT' else held_ids).add(oid)
        elif anchor['role']=='HELD_OUT':reasons.append('Held-out rows must bind independent measured canonical observations')
    # Every other known critical row remains independent held-out evidence.
    held_ids.update(e['observation_id'] for e in candidate['evidence'] if e['critical'] and e['observation_id'] not in fit_ids)
    raw_values=[];after_values=[];corrections=[];fit_corrections=[];held_corrections=[]
    for e in candidate['evidence']:
        pixel=e['pixel'];target=e['projected_affine'];q=(pixel[axis]-a)/(b-a)
        mapped=list(pixel);mapped[axis]=c+(d-c)*warp(q)
        projected=list(target);projected[axis]=a+(b-a)*warp.inverse((target[axis]-c)/(d-c))
        raw=math.dist(pixel,e['projected_raw']);after=math.dist(pixel,projected)
        correction=(warp(q)-q)*(b-a);corrections.append(correction)
        if e['observation_id'] in fit_ids:fit_corrections.append(correction)
        else:held_corrections.append(correction)
        feature={**e,'rectified_pixel':mapped,'raw_residual_px':raw,'rectified_residual_px':after}
        result.setdefault('feature_comparison',[]).append(feature)
        if e['observation_id'] in held_ids:
            passed=after<=e['tolerance_px']+1e-9 and after<=raw+1e-9
            result['held_out'].append({**feature,'delta_px':after-raw,'status':'PASS' if passed else 'FAIL','extrapolated':q<warp.x[0] or q>warp.x[-1]})
            raw_values.append(raw);after_values.append(after)
            if not passed:reasons.append('Held-out residual fails: '+e['id'])
    if len(held_ids)<2:reasons.append('At least two independent measured held-out observations are required')
    if raw_values and rms(after_values)>=rms(raw_values)-1e-9:reasons.append('Held-out RMS does not improve')
    critical=[e for e in result.get('feature_comparison',[]) if e['critical']]
    def summary(key):
        values=[e[key] for e in critical]
        return {'max_critical_px':max(values,default=None),'mean_critical_px':sum(values)/len(values) if values else None,
            'failed_critical':sum(e[key]>e['tolerance_px']+1e-9 for e in critical)}
    result.update(before={**summary('raw_residual_px'),'held_out_rms_px':rms(raw_values)},after={**summary('rectified_residual_px'),'held_out_rms_px':rms(after_values)},
        rms_fit_correction_px=rms(fit_corrections),rms_heldout_correction_px=rms(held_corrections),rms_all_landmark_correction_px=rms(corrections))
    if result['after']['failed_critical']:reasons.append('Individual critical correspondence failures remain')
    try:AxisRectification(r)
    except ReconError as exc:reasons.append(str(exc))
    result['eligible']=not reasons;result['status']='ELIGIBLE_FOR_ACTIVATION' if not reasons else 'EVALUATED'
    max_change=max(abs(lo-1),abs(hi-1))
    result['distortion']='EXCESSIVE' if max_change>limit+SCALE_EPSILON else 'BORDERLINE' if max_change>=limit*.9 else 'SMALL / ACCEPTABLE'
    return result

def activation(workspace,candidate):
    if candidate['status']=='REJECTED' or not current(workspace,candidate):raise ConflictError('Rejected or STALE candidate cannot activate')
    fresh=make_candidate(workspace,candidate['request'],ident=candidate['id'],creator=candidate['creator'])
    report=evaluate(fresh)
    if not report['eligible']:raise ReferenceError('Rectification is not eligible: '+'; '.join(report['reasons']))
    return report['model']
