"""Record the completed visual review; deliberately separate from mask metrics.

Run only after inspecting surface-only, reflection-stripe, matcap and all
five model renders. The reviewer notes and proof hashes remain auditable.
"""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/'validation/report.json').read_text())
audit=json.loads((ROOT/'validation/geometry_audit.json').read_text())
source_hash=hashlib.sha256((ROOT/'tesla_surface_model.blend').read_bytes()).hexdigest()
assert report['silhouette_pass'] and audit['finite_and_nonzero_faces']
assert report['source_blend_sha256']==source_hash
proofs={name:hashlib.sha256((ROOT/'validation'/name).read_bytes()).hexdigest() for name in ('surface_reflections.png','surface_matcap.png','perspective_surface.png','front.png','side.png','rear.png','top.png','perspective.png')}
review={'status':'PASS','method':'Visual review of actual Blender SubD, studio, reflection-coordinate stripes and Workbench matcap renders',
    'source_blend_sha256':source_hash,'proof_sha256':proofs,
    'reviewed_zones':['hood crown and shoulder','roof and windshield','front/rear fender crowns and geometric arch returns','door centers and panel seams','C-pillar and rear-quarter transition','front and rear fascia cavities'],
    'scope':'Visual reference reconstruction and SubD surface presentation; no numerical G2 or manufacturing certification asserted.',
    'source_limits':['End-view horizontal rectification and greenhouse width reconciliation documented in reference_dimensions.md','Scale assumes 4.8m length','Illustrative source views disagree in tire sizes, roof width and mirror projection'],
    'topology_quad_percent':audit['surface_control_mesh']['quad_percent']}
(ROOT/'validation/surface_review.json').write_text(json.dumps(review,indent=2),encoding='utf-8')
report.update(status='validated_model_export_ready',surface_quality_pass=True,export_allowed=True,surface_review='surface_review.json',complete=False)
(ROOT/'validation/report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('VISUAL_REVIEW_RECORDED; source geometry bound to report by SHA-256')
