> Historical first-pass notes. Current correction results: [cage_correction_report.md](cage_correction_report.md), [cage_residuals.md](cage_residuals.md).

# Mark II first portability pass — stopped at cage review

Status: **BLOCKED**. Portability has not been proven. The standard CLI reached
stage 05, but the resulting cage failed explicit visual acceptance. No surfaces,
details, GLB, viewer or final delivery were executed after that decision.

## Dimension research

The [Toyota E-JZX100 Tourer V catalog](https://toyota.jp/ucar/catalog/brand-TOYOTA/car-MARK_II/199609/1001095/)
lists stock length/width/height 4760/1755/1400 mm and wheelbase 2730 mm.
[Toyota's eighth-generation history](https://www.toyota-global.com/company/history_of_toyota/75years/vehicle_lineage/car/id60013052/index.html)
corroborates these dimensions. The stock wheelbase is used as a scale anchor,
assuming the custom X100-inspired chassis retains it. It is not a measured
dimension of the illustrated build. The bodykit envelope and stance are derived
from the supplied imagery instead of substituting the stock envelope.

Image estimates: length approximately 4.54 m, width 2.04 m, height 1.24 m,
tire radius 0.309 m, front overhang 0.818 m, rear overhang 0.992 m.
Calibration records preserve uncertainty and the declared TOP transverse
rectification. These are reconstruction estimates, not precise OEM bodykit
specifications.

## Required failure

The cage is a first authored candidate. Passing schema/cardinality checks and
constructing curves does not establish a matching vehicle. Actual overlays show:

- SIDE: the lower leading corner of the front door is too far forward. An
  independent source observation is approximately (591,648) px, with 5 px
  uncertainty. The exact projected cage coordinate and residual are recorded in
  `cage_review.json`; the displacement is about 33 px.
- FRONT/REAR: greenhouse and pillar widths are visibly too broad relative to
  the source. The candidate is not accepted as a coherent four-view cage.
- TOP: roof/window boundaries need reconciliation with the side/end views.
  The source is visibly oblique. Neither a source correction nor an adjustment
  of the IoU floors has been accepted to conceal these discrepancies.

These are unresolved authoring/reference-fit findings. No existing surface
operation has been demonstrated incapable of representing the vehicle. A new
operation or framework extension is not justified by this failed candidate.
No `framework_gap_report.md` proposing a speculative extension was created.

## What exists

- Four metric affine calibration records, packed references, five cameras and
  aligned proof images; ground and shared wheel geometry are recorded.
- 56 cage records: 48 rails, 4 transverse sections and 4 arch boundaries.
  Symmetry plus wheel guides expands these to 116 actual Blender curves.
- 80 bounded graph nodes / 28 semantic patch definitions, authored but unbuilt.
- 27 detail component definitions, authored for preflight but unexecuted.
- `output/mark2_calibrated.blend` and `output/mark2_cage_review.blend`, both
  checkpoint copies. They are not a finished or accepted vehicle asset.

The scene has no dense body mesh. No GLB, browser viewer or delivery manifest
exists. Their absence follows the required stop, not a claimed exporter failure.

## Execution and cache

`init --profile sedan` succeeded. The corrected project data pass the existing
schemas, pure calibration/cage checks, graph evaluation and detail-record
checks. An early JSON serialization error joined two dependency names into one
string; it was corrected in project data before the successful stage 01–04 run.
No core change or gate bypass was used.

The successful first run through overlay has four PASS results. The subsequent
incremental run through cage reports preflight PASS, references SKIP, calibration
PASS, overlay SKIP and cage PASS. That last PASS means the CLI built the curve
records; the separate explicit visual review is FAIL. The complete pipeline
and its full second-run cache acceptance were not run beyond this failure.

## Freeze and next boundary

`vehiclerecon/`, `schemas/` and `profiles/` remain identical to base commit
`060309de6014a760339ab100e4d61ecece102b72`. No project-specific Python was created
and no source-package Python was read or executed. Only the reference images
and reference documents were consulted. Tesla geometry/data were not reused.

Required before another modeling pass: review the failed overlays, correct the
Mark II feature records and reconcile the four-view greenhouse proportions.
Keep the existing target floors and the core freeze. Dense reconstruction must
remain blocked until the cage is accepted.
