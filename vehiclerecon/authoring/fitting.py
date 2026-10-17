"""Deterministic constrained raw-pixel landmark proposals; no canonical writes."""
import math
import numpy as np
from ..core.errors import SchemaError
from ..core.project import finite
from ..reference.transforms import CalibrationTransform
from .contracts import observations, observed_pixel
from .projection import residual


def fit_landmark(calibration, observation_ids, *, constraints=None, excluded_ids=(), weights=None,
                 tolerance_px=2., initial=None, links=None):
    """Huber IRLS/Gauss-Newton in raw pixels with exact affine constraints.

    Projection and optional rectification use CalibrationTransform exclusively.
    Constraints are {axis: X/Y/Z, value: metres} or {normal:[...], offset:metres}.
    An SVD null space enforces planes exactly. No invented single-view depth.
    """
    finite([constraints,weights,tolerance_px,initial])
    if not isinstance(observation_ids,list) or not 1<=len(observation_ids)<=256 or len(set(observation_ids))!=len(observation_ids):
        raise SchemaError('Select 1..256 distinct observation IDs')
    if isinstance(tolerance_px,bool) or not isinstance(tolerance_px,(int,float)) or tolerance_px<=0:
        raise SchemaError('Positive declared fit tolerance required')
    constraints=constraints or [];weights=weights or {};links=links or {}
    if len(constraints)>3 or set(weights)-set(observation_ids) or set(excluded_ids)-set(observation_ids):
        raise SchemaError('Invalid constraints, exclusions or weight identities')
    transform=CalibrationTransform(calibration);available=observations(calibration)
    used=[];excluded=[];matrices=[];targets=[];a=[];b=[]
    for c in constraints:
        if set(c)=={'axis','value'} and c['axis'] in ('X','Y','Z'):
            normal=[float(i=='XYZ'.index(c['axis'])) for i in range(3)];offset=c['value']
        elif set(c)=={'normal','offset'} and len(c['normal'])==3:
            normal=c['normal'];offset=c['offset']
        else:raise SchemaError('Explicit axis value or plane normal/offset required')
        if not all(type(x) in (int,float) and math.isfinite(x) for x in (*normal,offset)) or np.linalg.norm(normal)<1e-12:
            raise SchemaError('Invalid exact constraint')
        a.append(normal);b.append(offset)
    if a:
        a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
        _,s,vt=np.linalg.svd(a,full_matrices=True);rank=int(sum(s>max(s[0]*1e-10,1e-12)))
        origin=np.linalg.lstsq(a,b,rcond=1e-10)[0]
        if np.max(np.abs(a@origin-b))>1e-9:raise SchemaError('Exact constraints conflict')
        null=vt[rank:].T
    else:origin=np.zeros(3);null=np.eye(3)
    for ident in observation_ids:
        if ident not in available:raise SchemaError('Observation missing: '+ident)
        o=available[ident];link=links.get(ident,{'id':ident})
        reason='Excluded by user' if ident in excluded_ids else None
        if calibration.get('source_sha256') and o['source_sha256']!=calibration['source_sha256']:reason='Reference has no declared registration to this calibration'
        if o['visibility'] in ('occluded','unobserved'):reason='Observation unavailable'
        elif o['visibility']=='inferred' or not o['measured']:reason='Inferred evidence is not an independent measurement'
        try:pixel=observed_pixel(o,link)
        except Exception as exc:
            raise SchemaError('Select a point or an explicitly bound source knot: '+ident) from exc
        if pixel is None:reason=reason or 'Unknown pixel'
        if reason:excluded.append({'observation_id':ident,'reason':reason});continue
        weight=weights.get(ident,1.)
        if type(weight) not in (int,float) or not math.isfinite(weight) or weight<=0:raise SchemaError('Fit weights must be finite and positive')
        # Zero declared pixel uncertainty means exact input resolution, not infinite weight.
        sigma=max(float(o['uncertainty_px']),.25)
        d=transform.views[o['view']];basis=np.asarray([d['u_basis'],d['v_basis']],dtype=float).T
        linear=np.linalg.pinv(basis)@np.diag([1,link.get('side',1),1])
        rectified=np.asarray(pixel,dtype=float).copy()
        if o['view'] in transform.rectifications:
            warp=transform.rectifications[o['view']];rectified[warp.axis]=warp.forward(rectified[warp.axis])
        matrices.extend(linear);targets.extend(rectified+np.linalg.pinv(basis)@np.asarray(d['origin']))
        used.append({'observation_id':ident,'view':o['view'],'pixel':pixel,'weight':weight,'sigma_px':sigma,
                     'side':link.get('side',1),'allowed_px':link.get('tolerance_policy',{}).get('allowed_px',tolerance_px)})
    base={'observations_used':[u['observation_id'] for u in used],'observations_excluded':excluded,
          'constraints':constraints,'tolerance_px':tolerance_px,'method':'Huber IRLS raw-pixel Gauss-Newton, exact constraint null space',
          'proposal_only':True,'rows':[],'proposed_xyz':None,'rms_residual_px':None,'max_residual_px':None}
    if not used or (len(used)<2 and not constraints):
        return {**base,'status':'UNDERCONSTRAINED','conditioning':{'rank':0,'free_dimensions':null.shape[1],'condition_number':None},
                'ambiguity':'Another calibrated view or an explicit plane/axis value is required'}
    m=np.asarray(matrices,dtype=float);target=np.asarray(targets);scales=np.repeat([math.sqrt(u['weight'])/u['sigma_px'] for u in used],2)
    design=m@null;sv=np.linalg.svd(design*scales[:,None],compute_uv=False)
    rank=int(sum(sv>max(sv[0]*1e-10,1e-10))) if len(sv) else 0
    condition=float(sv[0]/sv[-1]) if len(sv) and rank==null.shape[1] and sv[-1]>0 else None
    base['conditioning']={'rank':rank,'free_dimensions':null.shape[1],'condition_number':condition,'singular_values':sv.tolist()}
    if rank<null.shape[1] or (condition is not None and condition>1e8):
        return {**base,'status':'UNDERCONSTRAINED','ambiguity':'Calibrated evidence does not determine every unconstrained world coordinate'}
    q=np.linalg.lstsq(design*scales[:,None],(target-m@origin)*scales,rcond=1e-10)[0]
    def projected(x):
        return np.asarray([v for u in used for v in transform.world_to_pixel(u['view'],x[0],x[1]*u['side'],x[2])])
    observed=np.asarray([v for u in used for v in u['pixel']])
    def loss(r):
        lengths=np.linalg.norm((r*scales).reshape(-1,2),axis=1);delta=1.345
        return float(np.sum(np.where(lengths<=delta,.5*lengths**2,delta*(lengths-.5*delta))))
    iterations=0
    for iterations in range(40):
        x=origin+null@q;r=projected(x)-observed
        if null.shape[1]==0:break
        jac=np.column_stack([(projected(x+null[:,i]*1e-6)-projected(x-null[:,i]*1e-6))/2e-6 for i in range(null.shape[1])])
        norms=np.linalg.norm((r*scales).reshape(-1,2),axis=1)
        robust=np.repeat(np.sqrt(np.minimum(1.,1.345/np.maximum(norms,1e-12))),2)*scales
        step=np.linalg.lstsq(jac*robust[:,None],-r*robust,rcond=1e-10)[0]
        if np.linalg.norm(step)<1e-10:break
        current=loss(r);accepted=False
        for power in range(16):
            candidate=q+step*(.5**power)
            if loss(projected(origin+null@candidate)-observed)<=current+1e-12:
                q=candidate;accepted=True;break
        if not accepted:break
    xyz=origin+null@q;rows=[]
    for u in used:
        p=transform.world_to_pixel(u['view'],xyz[0],xyz[1]*u['side'],xyz[2])
        rows.append({'observation_id':u['observation_id'],'view':u['view'],'observed_pixel':u['pixel'],
                     'projected_pixel':list(p),**residual(u['pixel'],p,u['allowed_px'])})
    distances=[r['residual_px'] for r in rows]
    return {**base,'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL',
            'proposed_xyz':xyz.tolist(),'rows':rows,'rms_residual_px':math.sqrt(sum(d*d for d in distances)/len(distances)),
            'max_residual_px':max(distances),'iterations':iterations+1,'initial_xyz':initial,'ambiguity':None}


def place_on_plane(calibration,view,pixel,normal,offset):
    """Intersect the calibrated pixel ray with an explicit world plane."""
    from ..core.project import finite
    finite([pixel,normal,offset])
    transform=CalibrationTransform(calibration);d=transform.views[view]
    n=np.cross(d['u_basis'],d['v_basis']);n=n/np.linalg.norm(n)
    normal=np.asarray(normal,dtype=float)
    if normal.shape!=(3,) or np.linalg.norm(normal)<1e-12:raise SchemaError('A finite nonzero plane normal is required')
    denominator=float(normal@n)
    if abs(denominator)<1e-10:raise SchemaError('Depth is underdetermined: the pixel ray is parallel to the supplied plane')
    p=np.asarray(transform.pixel_to_world(view,*pixel));return (p+n*(offset-normal@p)/denominator).tolist()
