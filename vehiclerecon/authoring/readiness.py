"""Deterministic readiness/invalidation reports without running a pipeline."""
from ..core.errors import ReconError, BlockedError
from ..core.project import Project
from ..reference.calibration import load
from ..reference.panels import png_size
from .workspace import Workspace
from .reviews import review_status
from .projection import coverage, residual_report


def _state(reasons):
    return {'state':'BLOCKED' if reasons else 'READY','reasons':reasons}


def readiness(root, *, workspace=None):
    """Reuse a current validated Workspace for derived feedback, without reloading."""
    if workspace is not None:
        from pathlib import Path
        from ..core.revisions import revision
        from ..core.errors import ConflictError
        if Path(root).resolve()!=workspace.root or revision(root)!=workspace.revision:
            raise ConflictError('Readiness snapshot changed; reload workspace')
    project = workspace.project if workspace is not None else Project(root)
    if project.data['schema_version']==1:
        return {'schema_version':1,'read_only_authoring':True,'legacy_behavior_unchanged':True,
                'source_review':{'state':'BLOCKED','required':False,'reasons':['v1 has no v2 authoring acceptance guarantee']}}
    w = workspace if workspace is not None else Workspace(root)
    data = w.documents;result = {'schema_version':2,'revision':w.revision,'read_only_authoring':False}
    reasons = []
    if not project.data['references']:reasons.append('No imported references')
    for path in project.data['references'].values():
        try:png_size(project.path(path,exists=True))
        except (ReconError,OSError,ValueError) as exc:reasons.append(str(exc))
    result['references'] = _state(reasons)
    reasons = []
    if 'calibration' not in data:reasons.append('Calibration authoring missing')
    else:
        try:
            from ..reference.calibration import check_config
            check_config(project,data['calibration'])
        except (ReconError,OSError,KeyError,TypeError,ValueError) as exc:reasons.append('Incomplete/inconsistent calibration: '+str(exc))
        for view,entry in data['calibration']['views'].items():
            if entry.get('source_state')=='CALIBRATION_REQUIRED':reasons.append(view+': replacement source framing requires explicit recalibration')
    result['calibration'] = _state(reasons)
    reasons = []
    if 'cage' not in data or not data['cage']['curves']:reasons.append('Shared cage curves not authored')
    if result['calibration']['state']!='READY':reasons.append('Calibrated projection unavailable')
    result['cage'] = _state(reasons)
    for kind in ('source','cage'):
        result[kind+'_review'] = review_status(w,kind)
    reasons = []
    for component in ('references','calibration','cage','source_review','cage_review'):
        if result[component]['state']!='READY':reasons.extend(result[component]['reasons'])
    if 'surface_graph' not in data:reasons.append('Bounded surface graph missing')
    result['surfaces'] = _state(reasons)
    result['unknown_dimensions'] = [k for k,v in project.data['dimensions'].items() if k.endswith('_m') and v is None]
    return result


def invalidation(scopes):
    from ..core.pipeline import STAGES
    seeds = set();reviews = set();diagnostics = set()
    for scope in scopes:
        if scope in ('observations','correspondences','measurements','calibration','policy','rectification'):
            seeds.add('calibration');reviews.update(('source','cage','final'));diagnostics.add('projection')
        elif scope in ('cage','world'):
            seeds.add('cage');reviews.update(('cage','final'));diagnostics.add('projection')
        elif scope=='references':
            seeds.add('references');reviews.update(('source','cage','final'));diagnostics.add('projection')
        elif scope=='surface_graph':seeds.add('surfaces');reviews.add('final')
        elif scope=='details':seeds.add('details');reviews.add('final')
        elif scope=='viewer':seeds.add('viewer')
        elif scope in ('source_review','cage_review'):seeds.add('surfaces');reviews.update(('cage','final') if scope=='source_review' else ('final',))
    affected = set(seeds)
    for stage in STAGES:
        if any(dep in affected for dep in stage.dependencies):affected.add(stage.id)
    return {'stages':[s.id for s in STAGES if s.id in affected],'reviews':sorted(reviews),
            'diagnostics':sorted(diagnostics),'geometry_remains_valid':not bool(affected-{'viewer','delivery'})}
