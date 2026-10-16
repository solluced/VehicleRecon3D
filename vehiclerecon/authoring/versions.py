"""Explicit, backed-up v1 -> v2 migration; opening never migrates."""
import base64
import copy
import json
import uuid
from pathlib import Path
from ..core.project import Project, read_json, validate, RESOURCE_ROOT
from ..core.errors import SchemaError, ConflictError
from ..core.locking import ProjectLock
from ..core.revisions import revision, snapshot, safe_path
from ..core.transactions import atomic_write, commit, digest
from ..core.manifest import digest_data
from .workspace import Workspace, REVIEWS

SUPPORTED_VERSIONS = (1, 2)


def inspect_version(root):
    with ProjectLock(root, 'version-inspection'):
        data = read_json(safe_path(root, 'project.json'))
        version = data.get('schema_version')
        supported = type(version) is int and version in SUPPORTED_VERSIONS
        issues = []
        if supported:
            try:validate(data, 'project')
            except SchemaError as exc:issues.append(str(exc))
        else:issues.append('Unsupported schema_version; read-only')
        return {'version': version, 'supported_versions': list(SUPPORTED_VERSIONS),
                'supported': supported, 'valid': supported and not issues,
                'read_only': not supported or version == 1, 'issues': issues,
                'revision': revision(root)}


def _bytes(value):
    return (json.dumps(value, indent=2, allow_nan=False)+'\n').encode('utf-8')


def preview_migration(root, *, target=2):
    with ProjectLock(root, 'migration-preview'):
        project = Project(root)
        if project.data['schema_version'] != 1 or target != 2:
            raise SchemaError('Only explicit legacy v1 -> authoring v2 migration is supported')
        changes = {}
        for kind in ('calibration', 'cage', 'surface_graph', 'details'):
            if kind in project.data['generated']:project.generated(kind)
        data = copy.deepcopy(project.data);data['schema_version'] = 2;data['authoring_state'] = 'DRAFT'
        changes['project.json'] = data
        if 'calibration' in data['generated']:
            cal = copy.deepcopy(project.generated('calibration'));cal['schema_version'] = 2
            for view in cal['views'].values():
                view['landmarks']['observations'] = []
                view['landmarks']['source_curves'] = []
            cal['datums']['measurements'] = []
            cal['correspondences'] = []
            cal['authoring_policy'] = {'coverage_confirmed': False, 'critical_correspondence_ids': [],
                                       'required_views': ['front','side','rear','top'], 'required_proofs': []}
            changes[data['generated']['calibration']] = cal
        if 'cage' in data['generated']:
            cage = copy.deepcopy(project.generated('cage'));cage['schema_version'] = 2
            for curve in cage['curves']:
                curve['point_ids'] = ['point_'+digest_data([curve['id'],i])[:24] for i in range(len(curve['points']))]
                curve['visibility'] = 'inferred'  # Legacy geometry has no independently typed visibility evidence.
            changes[data['generated']['cage']] = cage
        for path in REVIEWS:
            if project.path(path).is_file():changes[path] = None
        current = snapshot(root)
        changed = [{'path': path, 'old_sha256': digest(current.get(path)),
                    'new_sha256': digest(_bytes(value) if value is not None else None)}
                   for path, value in sorted(changes.items())]
        return {'source_version':1,'target_version':2,'source_revision':revision(root),
                'source_hashes':{p:digest(raw) for p,raw in current.items()},
                'changed_files':changed,'documents':changes,
                'warnings':['No source observations, correspondences or accepted authoring reviews were fabricated.',
                            'Legacy dimensional values and geometry are preserved; missing typed provenance needs manual review.',
                            'Legacy untyped source/cage review records, if any, are backed up and removed from active authoring paths.',
                            'The historical final visual review is not new v2 authoring acceptance.'],
                'manual_authoring_required':['typed observations','measurements/provenance','correspondences',
                                             'critical coverage policy','source review','cage authoring review']}


def execute_migration(root, *, target=2, expected_revision, fault=None):
    with ProjectLock(root, 'migration', expected_revision):
        if revision(root) != expected_revision:
            raise ConflictError('CONFLICT: migration source changed')
        plan = preview_migration(root, target=target)
        original = snapshot(root)
        backup_id = 'migration_'+uuid.uuid4().hex
        backup_path = '.cache/authoring/checkpoints/'+backup_id+'.json'
        sources = set(read_json(safe_path(root, 'project.json'))['references'].values())
        backup = {'schema_version':1,'checkpoint_id':backup_id,'source_version':1,'target_version':2,
                  'source_revision':expected_revision,'source_hashes':plan['source_hashes'],
                  'files':{p:base64.b64encode(raw).decode('ascii') for p,raw in original.items()
                           if raw is not None and p not in sources}}
        atomic_write(root, backup_path, _bytes(backup))
        validator = object.__new__(Workspace);validator.project = Project(root)
        result = commit(root, {p:_bytes(d) if d is not None else None for p,d in plan['documents'].items()},
                        expected_revision=expected_revision,validator=validator.validate,operation='migration',fault=fault)
        return {**{k:v for k,v in plan.items() if k != 'documents'}, **result,
                'backup':backup_path,'backup_id':backup_id}


def create_draft(root, *, profile='sedan'):
    import re
    root = Path(root).resolve();root.mkdir(parents=True, exist_ok=True)
    if not re.fullmatch('[a-z_]+',profile) or not (RESOURCE_ROOT/'profiles'/f'{profile}.json').is_file():
        raise SchemaError('Unknown automobile profile')
    with ProjectLock(root, 'create-v2-draft'):
        if (root/'project.json').exists():raise SchemaError('Project already exists')
        identity = re.sub('[^a-z0-9_]','_',root.name.lower())
        if not identity or not identity[0].isalpha():identity = 'vehicle_'+identity
        data = {'schema_version':2,'project_id':identity,'category':'automobile','vehicle_profile':profile,
                'asset_name':identity,'authoring_state':'DRAFT','references':{},'generated':{},
                'dimensions':{**{name:None for name in ('length_m','width_m','height_m','wheelbase_m')},
                              'provenance':'UNMEASURED: authoring required'}}
        validate(data,'project');atomic_write(root,'project.json',_bytes(data))
        return {'schema_version':2,'state':'DRAFT','revision':revision(root),'root':str(root)}
