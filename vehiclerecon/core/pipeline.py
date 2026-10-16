"""Stage result vocabulary; orchestration is introduced in phase 08."""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from .errors import ReconError,BlockedError,SchemaError,GateError
from .project import Project,read_json
from .manifest import write_json

class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    BLOCKED = "BLOCKED"

@dataclass
class StageResult:
    stage: str
    status: Status
    message: str = ""
    outputs: list = field(default_factory=list)

    @property
    def exit_code(self):
        return 0 if self.status in (Status.PASS, Status.SKIP) else 1

@dataclass(frozen=True)
class Stage:
    id: str
    label: str
    dependencies: tuple

STAGES=[Stage('preflight','01 PREFLIGHT',()),Stage('references','02 REFERENCES',('preflight',)),
        Stage('calibration','03 CALIBRATION',('references',)),Stage('overlay','04 OVERLAY EXTRACTION',('references',)),
        Stage('cage','05 CAGE',('calibration','overlay')),Stage('surfaces','06 SURFACES',('cage',)),
        Stage('silhouette','07 SILHOUETTE',('surfaces',)),Stage('details','08 DETAILS',('silhouette',)),
        Stage('geometry','09 GEOMETRY AUDIT',('details',)),Stage('presentation','10 PRESENTATION',('geometry',)),
        Stage('export','11 EXPORT',('presentation',)),Stage('glb_verify','12 GLB VERIFY',('export',)),
        Stage('viewer','13 VIEWER',('glb_verify',)),Stage('delivery','14 DELIVERY',('viewer',))]

def dependency_order(stages):
    by_id={s.id:s for s in stages};result=[];active=set();done=set()
    if len(by_id)!=len(stages):raise SchemaError('Duplicate pipeline stage')
    def visit(name):
        if name not in by_id:raise SchemaError(f'Missing stage dependency {name}')
        if name in active:raise SchemaError('Pipeline dependency cycle')
        if name in done:return
        active.add(name)
        for dependency in by_id[name].dependencies:visit(dependency)
        active.remove(name);done.add(name);result.append(by_id[name])
    for stage in stages:visit(stage.id)
    return result

class Pipeline:
    def __init__(self,project,*,blender=None,use_cache=True,implementation=None,observers=()):
        self.project=project;self.blender=blender;self.results=[];self.use_cache=use_cache;self.keys={};self.target='delivery'
        from .events import Events
        self.events=Events(observers);self.active_stage=None;self.control=None
        from .cache import StageCache
        self.cache=StageCache(project,implementation) if use_cache else None

    def blender_run(self,stage,source=None):
        from ..blender.runner import run
        return run(self.project,stage,source=source,executable=self.blender)

    def execute(self,stage):
        p=self.project
        if stage=='preflight':
            if p.data['schema_version']==2:
                from ..authoring.readiness import readiness
                report=readiness(p.root)
                if self.target=='preflight':return []
                names=[s.id for s in STAGES];rank=names.index(self.target)
                for component in ('references','calibration','cage'):
                    if rank>=names.index(component) and report[component]['state']!='READY':
                        raise BlockedError('; '.join(report[component]['reasons']))
                if rank>=names.index('calibration') and not all(k in p.data for k in ('scene','materials')):
                    raise BlockedError('Build scene/materials not authored; metric draft remains incomplete')
                for kind,first in [('surface_graph','surfaces'),('silhouette_traces','silhouette'),('details','details')]:
                    if rank>=names.index(first) and kind not in p.data['generated']:
                        raise BlockedError('Authoring data missing: '+kind)
                from ..blender.runner import discover,version
                if rank>=names.index('calibration'):discover(self.blender)
                return []
            from ..reference.calibration import load
            from ..cage.builder import records
            from ..surfaces.builder import order
            from ..details.builder import check
            from ..blender.runner import discover,version
            from ..viewer.qa import browser
            from .manifest import digest_file
            import sys
            for kind in ('calibration','cage','surface_graph','details','silhouette_traces'):
                if kind not in p.data['generated']:raise BlockedError(f'Authoring data missing: {kind}')
            load(p);records(p);order(p.generated('surface_graph')['nodes']);check(p.generated('details'));discover(self.blender)
            write_json(p.path('validation/runtime.json'),{'blender_executable':str(discover(self.blender)),
                       'blender_version':version(self.blender),'browser_executable_sha256':digest_file(browser()),
                       'python_version':sys.version.split()[0]})
            return ['validation/runtime.json']
        if stage=='references':
            from ..reference.panels import inventory
            write_json(p.path('validation/reference_inventory.json'),inventory(p))
            return ['validation/reference_inventory.json']
        if stage=='calibration':
            from ..reference.calibration import load
            config,transform=load(p);self.blender_run('calibration')
            width,height=config['source_size']
            error=max(abs(a-b) for view in config['views'] for q in [(0,0),(width/2,height/2),(width,height)] for a,b in zip(q,transform.world_to_pixel(view,*transform.pixel_to_world(view,*q))))
            if error>1e-9:raise GateError('Calibration roundtrip failed')
            write_json(p.path('validation/calibration_migration_report.json'),{'status':'PASS','max_pixel_roundtrip_error':error,'source_hash':config['source_sha256'],'uncertainty_preserved':config['uncertainty'],'fresh_scene':True,'reference_proof':'reference_alignment.png'})
            return ['.cache/calibration.blend','validation/reference_alignment.png','validation/calibration_migration_report.json',*[f'validation/alignment_{v}.png' for v in config['views']],*[f'generated/crop_{v}.png' for v in config['views']]]
        if stage=='overlay':
            self.blender_run('overlay');return ['generated/overlay_raw.json']
        if stage=='cage':
            self.blender_run('cage',p.path('.cache/calibration.blend'))
            return ['.cache/cage.blend','validation/cage_inventory.json',*[f'validation/cage_{v}.png' for v in ('front','side','rear','top','perspective')],*[f'validation/cage_overlay_{v}.png' for v in ('front','side','rear','top')]]
        if stage=='surfaces':
            self.authoring_gate()
            self.blender_run('surfaces',p.path('.cache/cage.blend'));return ['.cache/surfaces.blend']
        if stage=='silhouette':
            self.blender_run('surface_masks',p.path('.cache/surfaces.blend'))
            return ['validation/surface_migration_report.json',*[f'validation/surface_masks/{kind}_{v}.png' for v in ('front','side','rear','top') for kind in ('model','reference','comparison')]]
        if stage=='details':
            self.blender_run('details',p.path('.cache/surfaces.blend'));return ['.cache/details.blend']
        if stage=='geometry':
            self.blender_run('cleanup',p.path('.cache/details.blend'));self.blender_run('audit',p.path('.cache/cleaned.blend'))
            return ['.cache/cleaned.blend','validation/topology_cleanup.json','validation/geometry_audit.json']
        if stage=='presentation':
            from ..validation.report import review
            from .cache import input_slice
            inputs=input_slice(p,'presentation',include_review=False)
            dependencies={'geometry':self.keys.get('geometry','uncached')}
            key=self.cache.key('presentation_assets',inputs,dependencies) if self.cache else None
            entry=self.cache.hit('presentation_assets',key) if self.cache else None
            outputs=['output/'+p.blend.name,'validation/final_migration_report.json',*p.data['presentation']['review_proofs'],*[f'validation/final_masks/{kind}_{v}.png' for v in ('front','side','rear','top') for kind in ('model','reference','comparison')]]
            if not entry:
                self.blender_run('presentation',p.path('.cache/cleaned.blend'));self.blender_run('final_masks',p.blend)
                if self.cache:self.cache.store('presentation_assets',key,outputs,dependencies,inputs)
            audit=read_json(p.path('validation/geometry_audit.json'));review(p,audit['geometry_hash'])
            return outputs
        if stage=='export':
            from ..export.glb import export
            export(p,executable=self.blender);return ['output/'+p.glb.name,'output/export_manifest.json']
        if stage=='glb_verify':
            from ..export.verify import verify
            verify(p);return ['validation/glb_geometry_report.json']
        if stage=='viewer':
            from ..viewer.builder import build
            from ..viewer.qa import check
            build(p);check(p)
            return ['output/viewer.html','validation/viewer_build.json','validation/viewer_qa.json','validation/viewer_desktop.png','validation/viewer_mobile.png']
        if stage=='delivery':
            from .delivery import deliver
            deliver(p);return ['output/delivery_manifest.json','validation/delivery_report.json']
        raise SchemaError(f'Unknown pipeline stage: {stage}')

    def authoring_gate(self):
        if getattr(self.project,'data',{}).get('schema_version')==2:
            from ..authoring.workspace import Workspace
            from ..authoring.reviews import require_acceptance
            require_acceptance(Workspace(self.project.root))

    def run(self,*,actions=None,until=None):
        from contextlib import nullcontext
        from .locking import ProjectLock
        from .execution import current_execution, Cancelled
        self.control=current_execution()
        if self.control:self.events=self.control.events
        root=getattr(self.project,'root',None)
        with ProjectLock(root,'pipeline-build') if root else nullcontext():
            try:return self._run(actions=actions,until=until)
            except Cancelled:
                interrupted=[]
                if self.active_stage:
                    interrupted=[{'stage':self.active_stage,'activity':'INTERRUPTED','reason':'CANCELLED'}]
                    self.events.emit('stage_interrupted',stage=self.active_stage,reason='CANCELLED')
                completed={r.stage for r in self.results}
                self.interrupted=interrupted
                report={'status':'FAIL' if any(r.status==Status.FAIL for r in self.results) else 'BLOCKED','stages':[{'stage':r.stage,'status':r.status.value,'message':r.message,'outputs':r.outputs} for r in self.results],
                        'interrupted':interrupted,'unexecuted':[s.id for s in STAGES if s.id not in completed and s.id!=self.active_stage],
                        'reason':'Managed job cancellation; no artificial stage FAIL'}
                write_json(self.project.path('validation/pipeline_report.json'),report)
                raise

    def _run(self,*,actions=None,until=None):
        self.results=[];failed=False;self.target=until or 'delivery'
        cache=self.cache if actions is None else None
        for stage in dependency_order(STAGES):
            if self.control:
                self.control.token.check();self.control.stage=stage.id
            self.active_stage=stage.id if not failed else None
            if not failed:self.events.emit('stage_started',stage=stage.id)
            key=None;inputs={};dependencies={}
            if failed:
                result=StageResult(stage.id,Status.BLOCKED,'Required earlier gate failed or is blocked')
            else:
                try:
                    if stage.id=='surfaces':self.authoring_gate()
                    entry=None
                    if cache:
                        from .cache import input_slice
                        inputs=input_slice(self.project,stage.id)
                        dependencies={d:self.keys[d] for d in stage.dependencies}
                        key=cache.key(stage.id,inputs,dependencies)
                        entry=cache.hit(stage.id,key) if stage.id!='preflight' else None
                        if entry and stage.id=='presentation':
                            from ..validation.report import review
                            audit=read_json(self.project.path('validation/geometry_audit.json'))
                            review(self.project,audit['geometry_hash'])
                        if entry and stage.id=='delivery':
                            from .delivery import verify_manifest
                            if not verify_manifest(self.project):entry=None
                    if entry:
                        if self.control:self.control.token.check()
                        outputs=[v['path'] for v in entry['outputs']]
                        self.keys[stage.id]=entry['result_key']
                        result=StageResult(stage.id,Status.SKIP,'Verified cache outputs',outputs)
                    else:
                        outputs=(actions[stage.id]() if actions is not None else self.execute(stage.id)) or []
                        if self.control:self.control.token.check()
                        result=StageResult(stage.id,Status.PASS,outputs=outputs)
                        if cache:
                            saved=cache.store(stage.id,key,outputs,dependencies,inputs)
                            self.keys[stage.id]=saved['result_key']
                except BlockedError as exc:
                    result=StageResult(stage.id,Status.BLOCKED,str(exc));failed=True
                except (ReconError,OSError,ValueError,KeyError) as exc:
                    result=StageResult(stage.id,Status.FAIL,str(exc));failed=True
                if cache and result.exit_code and key:
                    cache.store(stage.id,key,[],dependencies,inputs,status=result.status.value,message=result.message)
            self.results.append(result)
            self.active_stage=None
            self.events.emit('stage_finished',stage=stage.id,result=result.status.value,message=result.message)
            self.events.emit('stage_progress',stage=stage.id,completed=len(self.results),total=len(STAGES))
            for path in result.outputs:
                if self.project.path(path).is_file():self.events.emit('artifact_created',stage=stage.id,path=path)
            print(f'{stage.label}: {result.status.value}'+(f' — {result.message}' if result.message else ''),flush=True)
            if until==stage.id:break
        report={'status':'FAIL' if any(r.exit_code for r in self.results) else 'PASS',
                'stages':[{'stage':r.stage,'status':r.status.value,'message':r.message,'outputs':r.outputs} for r in self.results]}
        write_json(self.project.path('validation/pipeline_report.json'),report)
        return 1 if report['status']=='FAIL' else 0
