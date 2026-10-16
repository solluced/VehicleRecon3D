"""Raw canonical authoring documents, separate from resolved build records."""
import copy
import json
from ..core.project import Project, read_json, validate
from ..core.errors import SchemaError
from .contracts import semantic_check

KINDS = ('calibration', 'cage', 'surface_graph', 'details', 'silhouette_traces')
REVIEWS = ('validation/source_review.json', 'validation/cage_review.json')


class Workspace:
    def __init__(self, root):
        from ..core.locking import ProjectLock
        with ProjectLock(root, 'authoring-read'):
            self._load(root)

    def _load(self, root):
        self.project = Project(root)
        if self.project.data['schema_version'] != 2:
            raise SchemaError('Writable authoring requires an explicit v2 migration')
        self.root = self.project.root
        self.files = {'project.json': (self.root/'project.json').read_bytes()}
        for kind, relative in self.project.data['generated'].items():
            if kind in KINDS:
                self.files[relative] = self.project.path(relative, exists=True).read_bytes()
        for relative in REVIEWS:
            path = self.project.path(relative)
            if path.is_file():
                self.files[relative] = path.read_bytes()
        from ..core.revisions import snapshot, candidate_path
        self.files.update({p:raw for p,raw in snapshot(self.root).items() if candidate_path(p) and raw is not None})
        self.documents = self.decode(self.files)
        self.validate(self.files)
        from ..core.revisions import revision
        self.revision = revision(self.root)

    @staticmethod
    def decode(files):
        project = json.loads(files['project.json'].decode('utf-8-sig'))
        result = {'project': project}
        for kind, path in project.get('generated', {}).items():
            if kind in KINDS and path in files:
                result[kind] = json.loads(files[path].decode('utf-8-sig'))
        return result

    def validate(self, files):
        documents = self.decode(files)
        data = documents['project']
        validate(data, 'project')
        if data['schema_version'] != 2:
            raise SchemaError('Authoring transactions require v2')
        p = copy.copy(self.project)
        p.data = data
        roles = set(p.profile['roles']+p.profile['optional_roles'])
        if set(data.get('roles', {}))-roles:
            raise SchemaError('Unknown profile role')
        for view, threshold in data.get('validation', {}).get('thresholds', {}).items():
            if threshold < p.profile.get('minimum_iou', {}).get(view, 0):
                raise SchemaError('Cannot weaken a profile floor')
        for path in data['references'].values():
            p.path(path, exists=True)
        for path in data['generated'].values():
            p.path(path)
            if path not in files:
                raise SchemaError('Declared canonical document is missing: '+path)
        for kind, value in documents.items():
            if kind not in ('project', 'silhouette_traces'):
                validate(value, kind)
                if kind in ('calibration', 'cage') and value['schema_version'] != 2:
                    raise SchemaError('v2 authoring requires v2 calibration/cage')
        if 'calibration' in documents and 'cage' in documents:
            semantic_check(p, documents['calibration'], documents['cage'])
        elif 'calibration' in documents:
            # Source-only drafts can be authored before the first world point.
            cal = documents['calibration']
            if cal['correspondences']:
                raise SchemaError('Correspondence requires a cage')
            semantic_check(p, cal, {'curves': [], 'landmarks': {}})
        for path in REVIEWS:
            if path in files:
                record = json.loads(files[path].decode('utf-8-sig'))
                validate(record, 'authoring_review')
                expected = 'source' if path == REVIEWS[0] else 'cage'
                if record['review_type'] != expected:
                    raise SchemaError('Review stored under wrong canonical identity')
        from ..core.revisions import candidate_path
        for path,raw in files.items():
            if candidate_path(path):
                candidate = json.loads(raw.decode('utf-8-sig'));validate(candidate,'rectification_candidate')
                if path != 'validation/rectification_candidates/'+candidate['id']+'.json':
                    raise SchemaError('Candidate ID/path mismatch')
        return documents
