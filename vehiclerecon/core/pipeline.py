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
    def __init__(self,project,*,blender=None):
        self.project=project;self.blender=blender;self.results=[]

    def blender_run(self,stage,source=None):
        from ..blender.runner import run
        return run(self.project,stage,source=source,executable=self.blender)

    def execute(self,stage):
        p=self.project
        if stage=='preflight':
            from ..reference.calibration import load
            from ..cage.builder import records
            from ..surfaces.builder import order
            from ..details.builder import check
            from ..blender.runner import discover
            for kind in ('calibration','cage','surface_graph','details','silhouette_traces'):
                if kind not in p.data['generated']:raise BlockedError(f'Authoring data missing: {kind}')
            load(p);records(p);order(p.generated('surface_graph')['nodes']);check(p.generated('details'));discover(self.blender)
            return []
        if stage=='references':
            from ..reference.panels import inventory
            write_json(p.path('validation/reference_inventory.json'),inventory(p))
            return ['validation/reference_inventory.json']
        if stage=='calibration':
            from ..reference.calibration import load
            config,transform=load(p);self.blender_run('calibration')
            width,height=config['source_size']
            error=max(abs(a-b) for view in config['views'] for q in [(0,0),(width/2,height/2),(width,height)] for a,b in zip(q,transform.world_to_pixel(view,*transform.pixel_to_world(view,*q))))
            if error>1e-9:raise GateError('Affine roundtrip failed')
            write_json(p.path('validation/calibration_migration_report.json'),{'status':'PASS','max_pixel_roundtrip_error':error,'source_hash':config['source_sha256'],'uncertainty_preserved':config['uncertainty'],'fresh_scene':True,'reference_proof':'reference_alignment.png'})
            return ['.cache/calibration.blend','validation/reference_alignment.png','validation/calibration_migration_report.json',*[f'validation/alignment_{v}.png' for v in config['views']],*[f'generated/crop_{v}.png' for v in config['views']]]
        if stage=='overlay':
            self.blender_run('overlay');return ['generated/overlay_raw.json']
        if stage=='cage':
            self.blender_run('cage',p.path('.cache/calibration.blend'))
            return ['.cache/cage.blend','validation/cage_inventory.json',*[f'validation/cage_{v}.png' for v in ('front','side','rear','top','perspective')],*[f'validation/cage_overlay_{v}.png' for v in ('front','side','rear','top')]]
        if stage=='surfaces':
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
            self.blender_run('presentation',p.path('.cache/cleaned.blend'));self.blender_run('final_masks',p.blend)
            audit=read_json(p.path('validation/geometry_audit.json'));review(p,audit['geometry_hash'])
            return ['output/'+p.blend.name,'validation/final_migration_report.json',*p.data['presentation']['review_proofs'],*[f'validation/final_masks/{kind}_{v}.png' for v in ('front','side','rear','top') for kind in ('model','reference','comparison')]]
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

    def run(self,*,actions=None,until=None):
        self.results=[];failed=False
        for stage in dependency_order(STAGES):
            if failed:
                result=StageResult(stage.id,Status.BLOCKED,'Required earlier gate failed or is blocked')
            else:
                try:
                    outputs=(actions[stage.id]() if actions is not None else self.execute(stage.id)) or []
                    result=StageResult(stage.id,Status.PASS,outputs=outputs)
                except BlockedError as exc:
                    result=StageResult(stage.id,Status.BLOCKED,str(exc));failed=True
                except (ReconError,OSError,ValueError,KeyError) as exc:
                    result=StageResult(stage.id,Status.FAIL,str(exc));failed=True
            self.results.append(result)
            print(f'{stage.label}: {result.status.value}'+(f' — {result.message}' if result.message else ''),flush=True)
            if until==stage.id:break
        report={'status':'FAIL' if any(r.exit_code for r in self.results) else 'PASS',
                'stages':[{'stage':r.stage,'status':r.status.value,'message':r.message,'outputs':r.outputs} for r in self.results]}
        write_json(self.project.path('validation/pipeline_report.json'),report)
        return 1 if report['status']=='FAIL' else 0
