# Mark II cage correction — unresolved reference correspondence

Historical cage-correction evidence. The current phase is recorded in
[reference_reconciliation_report.md](reference_reconciliation_report.md): a
generic rectification capability now exists, but the Mark II candidate was
rejected for extreme source distortion. The measurements below are unchanged.

Date: 2026-10-16. Primary source: unchanged `input/multiview.png`.

The axle/ground lock passes using the authoritative 2.730 m wheelbase, the
original 5 px SIDE/end uncertainties and 10 px TOP uncertainty. Greenhouse
corners have been corrected in one shared world-space cage. The measured
FRONT/REAR greenhouse corners now pass, but the TOP correspondence does not.
No individual failed landmark is compensated by a smaller error elsewhere.

## Independent longitudinal check

All coordinates below are original source-image pixels, observed before fitting
the revised cage. A and B identify the near-side roof/window pillar junctions.

| Observation | SIDE | TOP, near side |
| --- | --- | --- |
| Front axle | (494,625) | (455,1010) |
| Rear axle | (918,625) | (925,1026) |
| A-pillar roof junction | (692,491) | (640,944) |
| B-pillar roof junction | (765,489) | (777,947) |
| A-to-B horizontal span | 73 px | 137 px |
| Same-view wheelbase span | 424 px | 470 px |
| A-to-B / wheelbase | 0.17217 | 0.29149 |

Allowing both feature endpoints and both axle endpoints their complete declared
uncertainties gives deliberately conservative ratio intervals:

- SIDE: **0.14516–0.20048**.
- TOP: **0.23878–0.34889**.

The intervals do not overlap. Their minimum separation is about **0.1045 m**
at a 2.730 m wheelbase. Translation and a shared longitudinal affine scale
cannot remove this difference. The two roof junctions have almost equal SIDE
height; treating their discrepancy as an arbitrary depth offset is not an
accepted geometric correction. See `reference_consistency.json`.

This is a counterexample for the axle-locked longitudinal affine interpretation
and the stated semantic correspondences. It does not prove that every possible
perspective camera model is impossible. The visibly oblique TOP, its camera
interpretation and these correspondences require review or a consistent
orthographic replacement. No source pixels were locally warped to match the
candidate, and no separate geometry was fitted to each view.

## Acceptance boundary

The revised cage remains **FAIL**. The source conflict prevents accepting the
greenhouse/pillar landmarks. The known door leading-edge error is still
32.68 px: door cuts were deliberately not moved before pillar acceptance, as
required by the correction order. Other door-cut residuals remain visible in
the table and in red inferred curves. Their measured target positions were
not changed to make them pass.

No missing bounded surface operation has been established. These findings do
not justify changing the frozen framework or adding a vehicle-specific module.
No framework extension has been proposed as a substitute for reference review.

`cage_residuals.json` and `cage_residuals.md` contain every measured residual.
The four canonical orthographic proof PNGs contain the actual Blender cage
over the reference, green observation rings and red failed-residual arrows.
The 3Q image includes an explicitly uncalibrated hero inset for secondary
comparison; it is not an accepted geometric hero overlay.

Surfaces and details remain **NOT STARTED**. Their existing authored JSON
definitions have not been executed or updated to pretend that the cage passed.
