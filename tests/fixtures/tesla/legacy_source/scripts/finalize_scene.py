"""Store final scene organization and review limitations, without changing geometry."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project import *
s=bpy.context.scene;s.camera=bpy.data.objects['CAM_3Q']
s['model_status']='REFERENCE_CONSTRAINED_SUBD_RECONSTRUCTION'
s['cage_status']='COMPLETE_REVIEWED_IN_ORTHOGRAPHIC_OVERLAYS'
s['reference_calibration']='PASS_REGISTERED_WITH_DOCUMENTED_SOURCE_INCONSISTENCIES'
s['validation_report']='validation/report.json; manual surface review in validation/surface_review.json'
s['absolute_scale']='4.8m length assumed; normalized image ratios are authoritative'
for ob in bpy.data.objects:
    if ob.name.startswith('WIRE_'):ob.hide_render=False
for col in ('00_REFERENCE','01_CURVE_CAGE'):
    for ob in coll(col).objects:ob.hide_render=True;ob.hide_set(True)
notes=bpy.data.texts.get('READ_ME_FIRST');notes.clear()
notes.write('EV SURFACE RECONSTRUCTION\n\n'
    'Open camera CAM_3Q for the studio presentation. WIRE objects display actual quad control-mesh edges.\n'
    'The BODY_MASTER assembly retains separate editable SubD patches, doors and glass.\n'
    'Unhide 00_REFERENCE objects to inspect the packed calibrated image planes; unhide 01_CURVE_CAGE for 53 semantic curves.\n'
    'Length 4.8m is an assumed physical scale. The illustrative source sheet has cross-view inconsistencies; see docs/reference_dimensions.md.\n'
    'Validation uses actual fixed-camera geometry renders and manually traced source masks. It does not establish OEM dimensions or numerical G2 certification.\n'
    'See docs/modeling_notes.md, docs/validation_summary.md and validation/geometry_audit.json.\n')
save()
