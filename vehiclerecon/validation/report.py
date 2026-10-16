"""Explicit visual decisions bound to geometry, inputs and actual proof bytes."""
from ..core.errors import BlockedError,GateError
from ..core.project import validate,read_json
from ..core.manifest import digest_file,digest_data,write_json

def model_inputs_hash(project,scope='final'):
    data=project.data
    keys=('dimensions','materials','scene','presentation') if scope=='final' else ('dimensions','materials','scene')
    value={k:data[k] for k in keys}
    value['mask_exclusions']=data['export']['excluded_collections']
    if scope=='final':
        value['roles']=data['roles']
        value['model_collections']=data['export']['collections']
    value['generated']={k:digest_file(project.path(path,exists=True)) for k,path in data['generated'].items()
                        if k in (('calibration','cage','surface_graph','details','silhouette_traces') if scope=='final' else ('calibration','cage','surface_graph','silhouette_traces'))}
    value['references']={k:digest_file(project.path(path,exists=True)) for k,path in data['references'].items()}
    return digest_data(value)

def review(project,geometry_hash,*,check_schema=True):
    path=project.path('validation/review.json')
    if not path.is_file():raise BlockedError('Explicit visual review missing: validation/review.json')
    record=read_json(path)
    if check_schema:validate(record,'review')
    if record['decision']!='PASS':raise GateError('Visual reviewer rejected the output')
    if record['geometry_hash']!=geometry_hash or record['input_state_hash']!=model_inputs_hash(project):
        raise BlockedError('Visual review is stale for current geometry or inputs')
    required=set(project.data['presentation']['review_proofs'])
    if not required.issubset(record['proof_hashes']):raise BlockedError('Review omits required proof renders')
    for relative,digest in record['proof_hashes'].items():
        if digest_file(project.path(relative,exists=True))!=digest:
            raise BlockedError(f'Visual review proof changed: {relative}')
    return record

def record_review(project,*,reviewer,decision,notes,limitations):
    from ..core.locking import ProjectLock
    from ..core.project import Project
    with ProjectLock(project.root,'visual-review'):
        return _record_review(Project(project.root),reviewer=reviewer,decision=decision,notes=notes,limitations=limitations)

def _record_review(project,*,reviewer,decision,notes,limitations):
    evidence=read_json(project.path('validation/geometry_audit.json',exists=True))
    record={'schema_version':1,'reviewer':reviewer,'decision':decision,'notes':notes,
            'geometry_hash':evidence['geometry_hash'],'input_state_hash':model_inputs_hash(project),
            'proof_hashes':{path:digest_file(project.path(path,exists=True)) for path in project.data['presentation']['review_proofs']},
            'limitations':limitations}
    validate(record,'review')
    write_json(project.path('validation/review.json'),record)
    return record
