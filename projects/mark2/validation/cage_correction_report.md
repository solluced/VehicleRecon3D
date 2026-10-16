# Mark II cage correction report

Result: **CAGE FAIL; PORTABILITY BLOCKED**. Surfaces/details **NOT STARTED**.

## Physical scale

Official stock length/width/height: **4.760 / 1.755 / 1.400 m**; authoritative wheelbase **2.730 m**.
The visual image envelope is about 4.54 x 2.04 x 1.24 m; its width includes protruding tires.
Rough aero-body envelope excluding tires: about 4.54 x 1.82–1.90 x 1.24 m, not accepted as a physical measurement.
Stock structural width is separately recorded and is not inferred from a flare edge.

## Axle / ground lock

Front axle center: (-1.365000, 0.000000, 0.309057) m; rear: (1.365000, 0.000000, 0.309057) m.
Measured Blender wheelbase: 2.730000004 m; error 0.000000004172 m; declared tolerance 0.050 m.
Wheel radius: 0.309057 m; ground Z=0. Tracks: 1.855/1.880 m (image-derived custom stance, not OEM tracks).
Axles/ground: **PASS**. All relevant original 5/10 px observation limits remain unchanged.

## Residual acceptance

66 critical observations: **44 PASS / 22 FAIL**.
Maximum: **52.273 px**; mean: **10.397 px** (not an acceptance statistic).
Front-door leading edge: **32.680 px**, still FAIL. It was not moved before pillar acceptance.

| Roof landmark | SIDE px | TOP px | FRONT px | REAR px |
| --- | ---: | ---: | ---: | ---: |
| a_pillar_roof | 0.233 | 52.273 | 1.000 | not observable |
| b_pillar_roof | 0.000 | 29.243 | not observable | not observable |
| c_pillar_side_roof | 0.000 | 43.149 | not observable | not observable |
| c_pillar_rear_roof | 1.553 | 38.491 | not observable | 1.553 |

Measured greenhouse maxima: FRONT 1.000 px; REAR 3.998 px; SIDE 3.998 px; TOP 52.273 px.
The TOP failures remain individual failures; the end-view improvement does not compensate for them.
See cage_residuals.md/JSON for every reference pixel, actual projection, dx, dy, uncertainty and result.

## Why authoring stopped

Near-side A–B roof distance divided by wheelbase has non-overlapping conservative source intervals:
SIDE 0.14516–0.20048; TOP 0.23878–0.34889. See reference_discrepancies.md.
The current affine correspondence cannot be accepted at the existing limits. A source/camera/correspondence review is required; no separate geometry per view or nonlinear image warp was used.
Do not promote the already observed SIDE/end-view corrections to a whole-cage PASS.
Door cuts, detailed arch/bumpers and secondary feature correction stay deferred.

## Cage and proof artifacts

54 rails (48 feature rails + 3 deferred door cuts + 3 inferred pillar paths), 4 semantic sections, 4 arch boundaries.
20 control-marker records expand into 33 display curves. Total actual Blender curves: **161**.
Blue: authored visible rails; red: inferred; purple: sections; orange: controls.
FRONT/SIDE/REAR/TOP canonical PNGs show the reference underneath actual cage geometry, plus residual arrows.
The 3Q image has an uncalibrated hero inset only; no hero-overlay acceptance is claimed.
output/mark2_cage_corrected.blend opens with the cage and SIDE reference visible. It contains **zero body meshes**.

## Freeze, cache and scope

Framework core modified: **NO**. Project-specific Python files: **0**.
The official core/schema/profile tree remains identical to 060309de6014a760339ab100e4d61ecece102b72.
No surface/detail worker was invoked. Existing surface_graph.json/details.json remain unbuilt and require later reconciliation with the corrected cage.
No missing generic automotive operation has been established: **framework gaps: none demonstrated**.

The raw repeat verified preflight PASS + four SKIPs. Canonical annotated review PNGs are derived after that run, so the normal hash checks now invalidate cage image outputs. Raw CLI proofs are retained; reference/calibration/overlay cache outputs still verify. No cache keys were edited or forged.

Portability remains **BLOCKED** until every required cage gate and the full later pipeline pass.
