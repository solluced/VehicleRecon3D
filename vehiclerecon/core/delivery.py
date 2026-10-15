"""Current-artifact release checks and project-scoped output manifest."""
from .project import read_json
from .manifest import digest_file,manifest,write_json
from .errors import GateError,ReconError
from ..validation.geometry import require_audit
from ..validation.silhouette import require
from ..validation.report import review,model_inputs_hash
from ..viewer.builder import embedded_bytes

def verify_manifest(project):
    try:
        value=read_json(project.path('output/delivery_manifest.json',exists=True))
        if value['status']!='PASS' or not value['files']:return False
        return all(digest_file(project.path(item['path'],exists=True))==item['sha256'] for item in value['files'])
    except (OSError,KeyError,ValueError,ReconError):
        return False

def deliver(project):
    audit=read_json(project.path('validation/geometry_audit.json',exists=True));require_audit(audit)
    masks=read_json(project.path('validation/final_migration_report.json',exists=True))
    require(masks['views'],project.data['validation']['baseline_iou'],project.data['validation']['max_iou_regression'])
    review(project,audit['geometry_hash'])
    export=read_json(project.path('output/export_manifest.json',exists=True))
    glb=read_json(project.path('validation/glb_geometry_report.json',exists=True))
    qa=read_json(project.path('validation/viewer_qa.json',exists=True))
    blend_hash=digest_file(project.blend);glb_hash=digest_file(project.glb)
    if masks['source_blend_sha256']!=blend_hash or export['source_blend_sha256']!=blend_hash or glb['source_blend_sha256']!=blend_hash:
        raise GateError('Delivery source hashes are stale')
    if export['input_state_hash']!=model_inputs_hash(project) or masks['input_state_hash']!=model_inputs_hash(project):raise GateError('Delivery model inputs changed')
    if any(item['glb_sha256']!=glb_hash for item in [export,glb,qa]):raise GateError('Delivery GLB hashes disagree')
    if glb['status']!='PASS' or qa['status']!='PASS':raise GateError('GLB or browser QA failed')
    if embedded_bytes(project.path('output/viewer.html',exists=True).read_text())!=project.glb.read_bytes():raise GateError('Viewer model differs from GLB')
    report={'status':'PASS','project_id':project.data['project_id'],'source_blend_sha256':blend_hash,'glb_sha256':glb_hash,
            'geometry_hash':audit['geometry_hash'],'exact_embedded_glb':True,'viewer_desktop':'PASS','viewer_mobile':'PASS','iou':{k:r['iou'] for k,r in masks['views'].items()}}
    write_json(project.path('validation/delivery_report.json'),report)
    paths=[project.root/'project.json']
    for folder in ['input','generated','output','validation']:
        paths.extend(p for p in project.path(folder).rglob('*') if p.is_file() and 'execution' not in p.parts
                     and p.name not in ('delivery_manifest.json','pipeline_report.json','test_results.json') and p.suffix not in ('.log',))
    output={'schema_version':1,'status':'PASS','project_id':project.data['project_id'],'files':manifest(project.root,paths)}
    write_json(project.path('output/delivery_manifest.json'),output)
    return report
