"""Typed transactional authoring and reversible live-session command history."""
import copy
import json
from ..core.errors import SchemaError, ReferenceError, ConflictError
from ..core.project import validate
from ..core.locking import ProjectLock
from ..core.revisions import revision
from ..core.transactions import commit
from ..core.manifest import digest_data
from .workspace import Workspace
from .contracts import observations, crop_identity
from .reviews import make_review, PATHS
from .readiness import invalidation


def _bytes(value):
    return (json.dumps(value,indent=2,allow_nan=False)+'\n').encode('utf-8')


def _empty_calibration():
    return {'schema_version':2,'views':{},'datums':{'measurements':[]},'correspondences':[],
            'authoring_policy':{'coverage_confirmed':False,'critical_correspondence_ids':[],
                                'required_views':['front','side','rear','top'],'required_proofs':[]}}


def _empty_cage():
    return {'schema_version':2,'collection':'01_CAGE','curves':[],'landmarks':{},'sides':[['L',-1],['R',1]],
            'materials':[],'guides':[],'renders':[]}


class AuthoringSession:
    def __init__(self, root, *, observer=None):
        self.root = Workspace(root).root
        from ..core.events import Events
        self.undo_stack = [];self.redo_stack = [];self.events = Events([observer] if observer else [])

    @property
    def revision(self):
        return revision(self.root)

    def apply(self, commands, *, expected_revision):
        if not isinstance(commands,list) or not commands:
            raise SchemaError('A nonempty typed command list is required')
        with ProjectLock(self.root,'authoring-command',expected_revision):
            w = Workspace(self.root)
            if w.revision != expected_revision:raise ConflictError('CONFLICT: authoring revision changed externally')
            before = copy.deepcopy(w.files);scopes = set()
            for command in commands:
                validate(command,'authoring_command')
                scopes.add(self._apply(w,command))
                self._flush(w)
                w.validate(w.files)
            changes = {p:w.files.get(p) for p in set(before)|set(w.files) if before.get(p)!=w.files.get(p)}
            result = commit(self.root,changes,expected_revision=expected_revision,validator=w.validate)
            result['stale'] = invalidation(scopes)
            if result['changed_files']:
                self.undo_stack.append({'before':before,'after':copy.deepcopy(w.files),
                                        'before_revision':expected_revision,'after_revision':result['revision'],
                                        'scopes':scopes})
                self.redo_stack.clear()
            self._notify(result)
            return result

    def _notify(self, result):
        self.events.emit('project_changed',revision=result['revision'],stale=result['stale'])

    def _restore(self, entry, target, expected_revision):
        w = Workspace(self.root)
        if w.revision != expected_revision:raise ConflictError('CONFLICT: history branch changed externally')
        files = entry[target]
        changes = {p:files.get(p) for p in set(w.files)|set(files) if w.files.get(p)!=files.get(p)}
        result = commit(self.root,changes,expected_revision=expected_revision,validator=w.validate,operation=target)
        result['stale'] = invalidation(entry['scopes']);self._notify(result)
        return result

    def undo(self, *, expected_revision):
        if not self.undo_stack:raise ConflictError('Nothing to undo')
        entry = self.undo_stack[-1]
        if expected_revision != entry['after_revision']:raise ConflictError('Undo revision does not match history')
        result = self._restore(entry,'before',expected_revision)
        self.undo_stack.pop();self.redo_stack.append(entry)
        return result

    def redo(self, *, expected_revision):
        if not self.redo_stack:raise ConflictError('Nothing to redo')
        entry = self.redo_stack[-1]
        if expected_revision != entry['before_revision']:raise ConflictError('Redo revision does not match history')
        result = self._restore(entry,'after',expected_revision)
        self.redo_stack.pop();self.undo_stack.append(entry)
        return result

    @staticmethod
    def _ensure(w, kind):
        if kind not in w.documents:
            w.documents[kind] = _empty_calibration() if kind=='calibration' else _empty_cage()
            w.documents['project']['generated'][kind] = 'generated/'+kind+'.json'
        return w.documents[kind]

    @staticmethod
    def _flush(w):
        data = w.documents['project'];w.files['project.json'] = _bytes(data)
        w.project.data = copy.deepcopy(data)
        for kind in ('calibration','cage','surface_graph','details','silhouette_traces'):
            if kind in w.documents:w.files[data['generated'][kind]] = _bytes(w.documents[kind])

    @staticmethod
    def _touch(cal, selected):
        for observation in selected:
            observation['revision'] += 1
            for link in cal['correspondences']:
                if link['observation_id']==observation['id']:link['observation_revision'] = observation['revision']

    def _apply(self, w, c):
        op = c['type']
        if op in ('SetSourceDisposition','SetCageReview'):
            kind = 'source' if op=='SetSourceDisposition' else 'cage'
            record = make_review(w,kind,decision=c['decision'],reviewer=c['reviewer'],notes=c['notes'],expected_subject=c.get('expected_subject'))
            w.files[PATHS[kind]] = _bytes(record)
            return kind+'_review'
        if op == 'SetViewerLabel':
            w.documents['project'].setdefault('viewer',{})['title'] = c['title'];return 'viewer'
        if op == 'SetProjectSettings':
            w.documents['project'][c['section']] = copy.deepcopy(c['value'])
            return 'viewer' if c['section']=='viewer' else 'calibration'
        if op == 'SetProjectMetadata':
            w.documents['project'].update(copy.deepcopy(c['values']))
            return 'calibration'
        cal = self._ensure(w,'calibration')
        if op == 'RegisterReference':
            from ..core.manifest import digest_file
            from ..reference.panels import png_size
            path = w.project.path(c['path'],exists=True)
            if not c['path'].startswith('input/') or digest_file(path)!=c['sha256'] or png_size(path)!=c['size']:
                raise ReferenceError('Imported reference identity does not match immutable source bytes')
            refs = w.documents['project']['references'];old = refs.get(c['reference_id'])
            if old is not None and old!=c['path']:raise ConflictError('Reference role already assigned; import a new identity explicitly')
            refs[c['reference_id']] = c['path']
            if 'source' not in cal:
                cal.update(source=c['path'],source_size=c['size'],source_sha256=c['sha256'])
            for view in ('front','side','rear','top'):
                cal['views'].setdefault(view,{'crop':[0,0,*c['size']],
                    'landmarks':{'observations':[],'source_curves':[]}})
            return 'references'
        if op == 'AddObservation':
            if c['observation']['id'] in observations(cal):raise ConflictError('Observation ID already exists')
            data = cal['views'].setdefault(c['view'],{'landmarks':{}})
            data['landmarks'].setdefault('observations',[]).append(copy.deepcopy(c['observation']));return 'observations'
        obs = observations(cal)
        if op == 'SetObservationProperties':
            if c['observation_id'] not in obs:raise ReferenceError('Observation ID missing')
            o = obs[c['observation_id']];values = copy.deepcopy(c['values'])
            if values.get('view',o['view'])!=o['view']:
                group = 'observations'
                for field in ('observations','source_curves'):
                    entries = cal['views'][o['view']]['landmarks'].get(field,[])
                    if o in entries:entries.remove(o);group=field;break
                dest = cal['views'].setdefault(values['view'],{'landmarks':{}})
                dest['landmarks'].setdefault(group,[]).append(o)
                o['crop_id'] = crop_identity(o['reference_id'],dest.get('crop'))
            o.update(values);self._touch(cal,[o]);return 'observations'
        if op in ('MoveObservation','DeleteObservation'):
            if c['observation_id'] not in obs:raise ReferenceError('Observation ID missing')
            o = obs[c['observation_id']]
            if op=='MoveObservation':
                if o['kind'] not in ('point','circle'):raise SchemaError('MoveSplinePoint is required for a knot')
                o['pixel' if o['kind']=='point' else 'center'] = c['pixel'];self._touch(cal,[o])
            else:
                for view in cal['views'].values():
                    for field in ('observations','source_curves'):
                        view['landmarks'][field] = [x for x in view['landmarks'].get(field,[]) if x['id']!=o['id']]
            return 'observations'
        if op in ('AddWorldLandmark','MoveWorldLandmark','DeleteWorldLandmark'):
            cage = self._ensure(w,'cage');key = c['world_entity_id'];exists = key in cage['landmarks']
            if op=='AddWorldLandmark' and exists:raise ConflictError('World landmark ID already exists')
            if op!='AddWorldLandmark' and not exists:raise ReferenceError('World landmark ID missing')
            if op=='DeleteWorldLandmark':del cage['landmarks'][key]
            else:cage['landmarks'][key] = c['point']
            return 'world'
        if op == 'BindObservation':cal['correspondences'].append(copy.deepcopy(c['correspondence']));return 'correspondences'
        if op == 'UnbindObservation':
            matches = [l for l in cal['correspondences'] if l['id']==c['correspondence_id']]
            if not matches:raise ReferenceError('Correspondence ID missing')
            cal['correspondences'].remove(matches[0]);return 'correspondences'
        if op == 'SetTolerance':
            links = [l for l in cal['correspondences'] if l['id']==c['correspondence_id']]
            if not links:raise ReferenceError('Correspondence ID missing')
            links[0]['tolerance_policy']['allowed_px'] = c['allowed_px']
            links[0]['provenance'] = copy.deepcopy(c['provenance']);return 'policy'
        if op == 'SetCoveragePolicy':cal['authoring_policy'] = copy.deepcopy(c['policy']);return 'policy'
        if op == 'SetMeasurement':
            values = cal['datums'].setdefault('measurements',[]);m = copy.deepcopy(c['measurement'])
            old = next((v for v in values if v['id']==m['id']),None)
            if old and old.get('locked') and old!=m:raise ConflictError('Authoritative measurement is locked')
            if old:values[values.index(old)] = m
            else:values.append(m)
            if 'dimension' in c:
                if m['unit'] not in ('m','mm'):raise SchemaError('Physical project dimension requires m or mm')
                value = None if m['value'] is None else m['value']*(.001 if m['unit']=='mm' else 1)
                w.documents['project']['dimensions'][c['dimension']] = value
            return 'measurements'
        if op == 'SetCalibrationView':
            value = copy.deepcopy(c['data']);previous = cal['views'].get(c['view'],{}).get('landmarks',{})
            if any(k in value.get('landmarks',{}) for k in ('observations','source_curves')):
                raise SchemaError('Use observation commands to edit authored source objects')
            value['landmarks'] = {**previous,**value.get('landmarks',{})}
            for field in ('observations','source_curves'):
                for o in value['landmarks'].get(field,[]):
                    o['crop_id'] = crop_identity(o['reference_id'],value.get('crop'));self._touch(cal,[o])
            cal['views'][c['view']] = value;return 'calibration'
        if op in ('AddRectificationAnchor','RemoveRectificationAnchor'):
            path = 'validation/rectification_candidates/'+c['candidate_id']+'.json'
            candidate = json.loads(w.files[path]) if path in w.files else None
            if candidate is None:
                if op!='AddRectificationAnchor' or 'rectification' not in c:
                    raise ReferenceError('New candidate needs an explicit rectification model')
                candidate = {'schema_version':2,'id':c['candidate_id'],'view':c['view'],'status':'CANDIDATE',
                             'revision':0,'base_calibration_hash':digest_data(cal),'rectification':copy.deepcopy(c['rectification'])}
            anchors = candidate['rectification']['anchors']
            if op=='AddRectificationAnchor':
                if candidate['view']!=c['view']:raise SchemaError('Candidate view mismatch')
                if any(a['semantic']==c['anchor']['semantic'] for a in anchors):raise ConflictError('Anchor semantic ID already exists')
                anchors.append(copy.deepcopy(c['anchor']));anchors.sort(key=lambda a:a['image'])
            else:
                matches = [a for a in anchors if a['semantic']==c['semantic']]
                if not matches:raise ReferenceError('Candidate anchor missing')
                if matches[0]['image'] in (0,1) and matches[0]['world_normalized']==matches[0]['image']:
                    raise ConflictError('Datum anchors are locked')
                anchors.remove(matches[0])
            candidate['revision'] += 1;w.files[path] = _bytes(candidate);return 'candidate'
        if op in ('AddSplinePoint','MoveSplinePoint','DeleteSplinePoint','SplitSpline','MergeSpline'):
            return self._spline(w,cal,c)
        raise SchemaError('Unsupported authoring command: '+op)

    def _spline(self, w, cal, c):
        world = c['target']=='cage';op = c['type'];cage = self._ensure(w,'cage') if world else None
        entries = cage['curves'] if world else list(observations(cal).values())
        entity = next((e for e in entries if e['id']==c['entity_id']),None)
        if entity is None or 'points' not in entity:raise ReferenceError('Editable spline entity missing')
        def ids(e):return e['point_ids'] if world else [p['id'] for p in e['points']]
        if op != 'MergeSpline' and c['point_id'] not in ids(entity) and op!='AddSplinePoint':
            raise ReferenceError('Stable knot ID missing')
        changed = [entity]
        if op=='AddSplinePoint':
            if any(c['point_id'] in ids(e) for e in entries if 'points' in e):raise ConflictError('Point ID already exists')
            if c['after_point_id'] not in ids(entity):raise ReferenceError('Insertion anchor missing')
            index = ids(entity).index(c['after_point_id'])+1
            if len(c['point']) != (3 if world else 2):raise SchemaError('Wrong coordinate dimension')
            entity['points'].insert(index,c['point'] if world else {'id':c['point_id'],'pixel':c['point']})
            if world:entity['point_ids'].insert(index,c['point_id'])
        elif op=='MoveSplinePoint':
            if len(c['point']) != (3 if world else 2):raise SchemaError('Wrong coordinate dimension')
            changed = []
            for e in entries:
                if 'points' not in e or c['point_id'] not in ids(e):continue
                index = ids(e).index(c['point_id']);changed.append(e)
                if world:
                    point = e['points'][index]
                    if isinstance(point,dict):cage['landmarks'][point['landmark']] = c['point']
                    else:e['points'][index] = c['point']
                else:
                    knot = e['points'][index];delta = [a-b for a,b in zip(c['point'],knot['pixel'])]
                    for handle in ('left','right'):
                        if handle in knot:knot[handle] = [a+b for a,b in zip(knot[handle],delta)]
                    knot['pixel'] = c['point']
        elif op=='DeleteSplinePoint':
            index = ids(entity).index(c['point_id']);entity['points'].pop(index)
            if world:entity['point_ids'].pop(index)
        elif op=='SplitSpline':
            if any(e['id']==c['new_entity_id'] for e in entries):raise ConflictError('Split target ID already exists')
            index = ids(entity).index(c['point_id'])
            if index in (0,len(entity['points'])-1):raise SchemaError('Split needs an interior knot')
            other = copy.deepcopy(entity);other['id'] = c['new_entity_id'];other['points'] = other['points'][index:]
            entity['points'] = entity['points'][:index+1]
            if world:
                other['point_ids'] = other['point_ids'][index:];entity['point_ids'] = entity['point_ids'][:index+1]
                # The shared endpoint keeps its original stable ID/value.
                cage['curves'].append(other)
            else:
                other['revision'] = 1
                cal['views'][entity['view']]['landmarks'].setdefault('observations',[]).append(other)
            moved = set(ids(other)[1:])
            for link in cal['correspondences']:
                key = 'world_entity_id' if world else 'observation_id'
                point_key = 'point_id' if world else 'observation_point_id'
                if link[key]==entity['id'] and link.get(point_key) in moved:
                    link[key] = other['id']
                    if not world:link['observation_revision'] = other['revision']
        elif op=='MergeSpline':
            other = next((e for e in entries if e['id']==c['other_entity_id']),None)
            if other is None or other is entity or 'points' not in other:raise ReferenceError('Merge target missing/invalid')
            if ids(entity)[-1] != ids(other)[0] or entity['points'][-1] != other['points'][0]:
                raise ConflictError('Merge requires the same stable shared endpoint; no implicit rebind')
            compare = ('role','kind','symmetry','cyclic','handles','material','visibility') if world else ('view','kind','reference_id','source_sha256','semantic_role')
            if any(entity[k]!=other[k] for k in compare):raise ConflictError('Incompatible spline metadata')
            entity['points'] += other['points'][1:]
            if world:
                entity['point_ids'] += other['point_ids'][1:];cage['curves'].remove(other)
            else:
                for view in cal['views'].values():
                    for field in ('observations','source_curves'):
                        view['landmarks'][field] = [o for o in view['landmarks'].get(field,[]) if o['id']!=other['id']]
            for link in cal['correspondences']:
                key = 'world_entity_id' if world else 'observation_id'
                if link[key]==other['id']:link[key] = entity['id']
        if not world:self._touch(cal,changed)
        return 'cage' if world else 'observations'
