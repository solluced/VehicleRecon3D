"""Explicit canonical source/cage decisions and current evidence checks."""
import json
from ..core.manifest import digest_data, digest_file
from ..core.project import validate
from ..core.errors import BlockedError, ConflictError, SchemaError, ReconError
from .projection import coverage, residual_report

PATHS = {'source':'validation/source_review.json','cage':'validation/cage_review.json'}


def source_subject(workspace):
    # Hash the in-memory candidate bytes too: a transaction may not be on disk yet.
    import hashlib
    p = workspace.project;data = workspace.documents
    return digest_data({'references':{k:digest_file(p.path(path,exists=True)) for k,path in data['project']['references'].items()},
                        'calibration_sha256':hashlib.sha256(workspace.files[data['project']['generated']['calibration']]).hexdigest(),
                        'dimensions':data['project']['dimensions'],'profile':p.profile})


def proof_hashes(workspace, paths=None):
    paths = paths if paths is not None else workspace.documents['calibration']['authoring_policy']['required_proofs']
    result = {}
    for relative in paths:
        if not relative.startswith('validation/') or relative in PATHS.values():
            raise SchemaError('Proof must be a separate validation artifact')
        result[relative] = digest_file(workspace.project.path(relative,exists=True))
    return result


def subject(workspace, kind):
    if kind == 'source':return digest_data({'inputs':source_subject(workspace),'proofs':proof_hashes(workspace)})
    import hashlib
    data = workspace.documents
    return digest_data({'source_subject':source_subject(workspace),
                        'proofs':proof_hashes(workspace),
                        'source_review_sha256':hashlib.sha256(workspace.files.get(PATHS['source'],b'')).hexdigest(),
                        'cage_sha256':hashlib.sha256(workspace.files[data['project']['generated']['cage']]).hexdigest(),
                        'residual_evidence':digest_data(residual_report(data['calibration'],data['cage']))})


def evidence_hash(workspace, kind):
    data = workspace.documents
    return digest_data(coverage(data['calibration']) if kind == 'source' else residual_report(data['calibration'],data['cage']))


def review_status(workspace, kind):
    try:
        raw = workspace.files.get(PATHS[kind])
        if raw is None:return {'state':'BLOCKED','decision':None,'current':False,'reasons':[kind+' authoring review missing']}
        record = json.loads(raw.decode('utf-8-sig'));validate(record,'authoring_review')
        current = (record['review_type']==kind and record['subject_hash']==subject(workspace,kind)
                   and record['residual_evidence_hash']==evidence_hash(workspace,kind)
                   and record['proof_hashes']==proof_hashes(workspace,list(record['proof_hashes']))
                   and set(proof_hashes(workspace)).issubset(record['proof_hashes']))
        reasons = []
        if not current:reasons.append(kind+' authoring review is stale')
        if record['decision']!='ACCEPTED':reasons.append(kind+' decision is '+record['decision'])
        if coverage(workspace.documents['calibration'])['state']!='READY':reasons.append('Critical source coverage incomplete')
        if kind == 'cage':
            if review_status(workspace,'source')['state']!='READY':reasons.append('Current accepted source review required')
            if residual_report(workspace.documents['calibration'],workspace.documents['cage'])['status']!='PASS':
                reasons.append('Individual critical cage residuals do not pass')
        return {'state':'BLOCKED' if reasons else 'READY','decision':record['decision'],'current':current,'reasons':reasons}
    except (OSError,KeyError,ValueError,ReconError) as exc:
        return {'state':'BLOCKED','decision':None,'current':False,'reasons':[str(exc)]}


def make_review(workspace, kind, *, decision, reviewer, notes, expected_subject=None):
    if decision == 'ACCEPTED':
        if expected_subject is None or expected_subject != subject(workspace,kind):
            raise ConflictError('Inspected evidence subject missing/stale')
        if coverage(workspace.documents['calibration'])['state']!='READY':
            raise BlockedError('Cannot accept unauthored critical coverage')
        if kind == 'cage':
            if review_status(workspace,'source')['state']!='READY':raise BlockedError('Current accepted source review required')
            if residual_report(workspace.documents['calibration'],workspace.documents['cage'])['status']!='PASS':
                raise BlockedError('Individual critical residuals fail; cage cannot be accepted')
    record = {'schema_version':2,'review_type':kind,'decision':decision,'reviewer':reviewer,'notes':notes,
              'subject_hash':subject(workspace,kind),'proof_hashes':proof_hashes(workspace),
              'residual_evidence_hash':evidence_hash(workspace,kind)}
    validate(record,'authoring_review')
    return record


def require_acceptance(workspace):
    for kind in ('source','cage'):
        status = review_status(workspace,kind)
        if status['state']!='READY':raise BlockedError('; '.join(status['reasons']))
