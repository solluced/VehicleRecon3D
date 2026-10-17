# VehicleRecon Studio v0.2 — multi-view consistency and live cage

Launch `vehicle-recon studio --root projects`. Normal use needs the optional
Studio Python distribution and a WebGL-capable browser; Node and Blender are
not needed for authoring. See [installation](studio_development.md). The existing
[source editor](studio_user_manual_v0.1b.md) retains original image import,
layers, curves, properties and schema settings.

## Open coordinated views

Open a project and choose **Multi-view / 3D**. **Source editor** returns to the
original 2D tools. Legacy v1 stays READ ONLY and is never migrated automatically.
New v2 drafts can have unknown scale and uncalibrated views; these are labelled
unavailable, with no guessed transform. This phase consumes existing calibrated
core views; it does not add a calibration or rectification editor.

Choose Single view, 2-up split, Four-view grid, 2D + 3D split, or Four views + 3D.
Choose the active view and, in 2-up, its second view. Every 2D pane has independent
pan/zoom, Fit and 1:1. Middle drag or Space+drag pans; keyboard navigation targets
the active pane. Linked selection and semantic focus are optional. Pixel zoom is
never synchronized between differently framed images.

Each pane identifies view, source hash, crop, calibration and rectification state.
The workspace uses the exact calibrated source identity rather than an unrelated
surface/control target selected in Source editor. RAW SOURCE means original
pixels. An ACTIVE rectification badge means the core projection uses that mapping;
the canvas still displays original pixels. Rejected candidates remain inactive.
Unregistered helper images cannot count as calibrated critical evidence.

## Source observations versus world geometry

- **Move Observation** changes source pixels only. Drag a 2D point/knot; canonical
  world XYZ remains fixed and the residual changes.
- **Move World Landmark** changes canonical XYZ. Use explicit numeric coordinates
  or a constrained 3D gizmo. Relevant projections/residuals refresh after the
  single command commits. The mode never switches silently.

**+ Source point** marks an observation in the clicked view. Use Source editor
for full polyline/spline tools and layers. The coordinated workspace's Source tab
also exposes observation properties/provenance. Critical, required, optional and
inferred evidence carry explicit labels.

## Correspondences and coverage

Select a source point or explicit source-curve knot. Open **Correspondence**,
choose a canonical world landmark (or select a stable cage control in 3D), enter
pixel tolerance and evidence policy, then **Bind observation to world**. Choose
canonical Y, mirrored Y or centerline only for the intended existing instance.
Existing assignments require explicit Unbind; they are never silently replaced.
Several source observations may bind to one world entity.

Critical links are explicitly designated. **Confirm authored critical coverage**
records the user's coverage policy; it does not accept source/cage evidence,
invent missing views or weaken residual checks. The coverage matrix reports each
landmark/stable cage point across SIDE/TOP/FRONT/REAR. Missing evidence is distinct
from an inconsistent fit.

## Create or solve a world landmark

The World tab supports:

1. **New world landmark**, a stable ID and explicit XYZ in metres, then
   **Create explicit XYZ**. Values come from the user, never invisible-depth inference.
2. Select a calibrated source observation, specify a plane axis/value and choose
   **Preview plane placement**. Parallel/underdetermined rays are rejected.
3. Select two or more independent calibrated observations and **Solve from
   observations**. Optional exact axis constraints and explicit excluded IDs are
   supported; declared observation uncertainties supply weights.

A solve is a **PROPOSAL**, with a separate ghost preview. Inspect old/proposed XYZ,
per-view dx/dy/residual/tolerance, RMS, maximum, conditioning, exact constraints and
used/excluded observations. Parallel views or missing depth remain UNDERCONSTRAINED.
Robust fitting never hides an individual failing observation behind a low mean.

**APPLY proposal** executes one undoable core command. **CANCEL proposal** changes
no canonical files. Binding a new point remains separate. Proposals expire after
five minutes and belong to one project/tab/revision. Any canonical change or
conflict clears the local ghost. See the [solver math](multiview_fitting.md).

## Residuals and consistency

Solid markers are observations; hollow/cross markers are projections; connecting
lines are residuals. Toggle vectors, numeric labels and heatmap. States always
have accessible text equivalents:

| State | Residual / declared tolerance |
| --- | --- |
| PASS | below 0.8 |
| NEAR | 0.8 through 1 |
| FAIL | above 1 |
| UNKNOWN | unavailable projection/evidence |

NEAR is a warning band, not a changed acceptance tolerance. Critical failures
remain individual rows. Optional evidence cannot average a critical failure away.
Consistency sorts by severity and supports failure/view filters and semantic
search. Clicking a row focuses its entity in relevant 2D panes and 3D.

Summary groups categorize existing semantic names into axles, envelope,
greenhouse, pillars, doors and secondary features. A within-tolerance PASS can
still carry a NEAR warning. Silhouette alone never establishes consistency.

## Three.js cage preview

The preview shows X longitudinal, Y lateral, Z up, ground, world landmarks,
wheel guides, cage controls/sections and core-sampled curves. AUTO curves are
explicitly labelled approximate control polygons; Blender remains authoritative
for final handles and surfaces. Three.js owns interaction and rendering only.

Drag to orbit, right drag to pan, wheel to zoom. Fit all includes wheel guides;
FRONT/REAR/LEFT/RIGHT/TOP/3/4 presets are available. Pick a landmark, control or
curve to synchronize selection. Choose Move World Landmark and X/Y/Z or
XY/XZ/YZ for constrained translation. The gesture previews locally and commits
once on release. Failed writes restore canonical feedback. Symmetry planes and
mirrored counterparts are display-only; no implicit mirror command is invented.
WebGL errors are explicit; the separate source editor remains available.

## Source and cage reviews

The Review tab separates source from cage acceptance. Inspect input identities,
dimensions/provenance, calibration/rectification, coverage, critical failures,
revision and proof/subject identity. Current/stale state is visible.

Source decisions: ACCEPTED, NEEDS_CORRECTION, INCONSISTENT_SOURCE.
Cage decisions: ACCEPTED, NEEDS_CORRECTION. Both require a reviewer and nonempty
note. Acceptance is never automatic. Stale subjects/revisions are rejected.
Source acceptance does not accept the cage; cage acceptance requires current
source acceptance and individually passing critical evidence.

Surface readiness reports the existing core gate. Rejected/stale source or cage
evidence blocks surfaces before construction. Review decisions use core undo.
There is no surface editor or Blender build button in this release.

## Automotive and legacy diagnostics

Diagnostics shows front/rear axles, current world wheelbase, authoritative
measurement when present, and difference in millimetres. SIDE/TOP ratios normalize
semantic positions between shared axle datums; they never alter calibration.
Rectification status and candidate correction/local-scale ranges are visible
without an anchor editor.

Existing Mark II evidence opens read-only: axle checks pass declared tolerances,
FRONT/REAR greenhouse maxima are about 1/4 px, and individual SIDE/TOP pillar
conflicts remain visible. Source stays INCONSISTENT_SOURCE, rejected rectification
stays inactive, surfaces/details stay NOT STARTED. Legacy report identities are
checked against current source/calibration/cage before residuals are shown. This
demonstration is neither migration nor a repaired vehicle.

## Persistence and retention

Commands save transactionally through core. Undo/redo and expected revisions cover
bindings, world moves, fit application and reviews as well as source edits.
Ctrl+Z/Ctrl+Shift+Z and toolbar controls remain available. Studio retains at most
100 history edges / 32 MiB of unique document bytes per live session, evicting
oldest edges first. Core CLI defaults remain unlimited. Backend restart starts
new live history while preserving canonical IDs, bindings, XYZ and review records.

External changes stop writes, invalidate proposals and require **Reload canonical
state**. No automatic merge or overwrite occurs. Layout and independent viewports
remain presentation preferences in `.studio/session.json`. See
[release measurements](../validation/studio_v0.2/README.md) for tested hardware,
save latency and 100-edit memory retention.

Deferred: CV/SAM/ONNX, Smart Edge, Magic Select, automatic wheel detection, full
rectification editor, surface graph editor, Blender Render and Cyberpunk adapter.
