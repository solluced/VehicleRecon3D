# VehicleRecon Studio product specification

Status: architecture baseline for review, not a shipped application. Read with
[architecture](studio_architecture.md), [UI](studio_ui_spec.md) and
[roadmap](studio_roadmap.md). All behavior below is a target unless identified
as an existing core capability.

## Product outcome

A person can prepare, correct and validate a new automobile project visually,
then run the same deterministic VehicleRecon3D compiler used by the CLI. The
normal workflow does not require JSON editing or per-vehicle Python. CV reduces
repetitive annotation; human judgment resolves ambiguity. AI may explain or
suggest, but is optional and never accepts geometry or reviews on the user's
behalf. The environment remains useful with all providers disabled.

Success means fewer manual file edits and shorter correction cycles while
preserving source identity, one shared vehicle, visible uncertainty, strict gates
and reproducible builds. Measure these in a new-vehicle usability trial; do not
claim autonomous reconstruction or portability from this design alone.

Primary users are an automobile author correcting references, a modeler refining
feature curves/patches, and a reviewer deciding whether evidence is acceptable.
The first deployment is one local operator with one writable editor per project;
other tabs may inspect read-only. Remote collaboration is outside this baseline.

## End-to-end workflow and exit conditions

| Step | Person sees/does | Data/result and exit condition |
|---|---|---|
| New Vehicle | Name and core body-profile choice | Canonical draft; unknown dimensions stay unknown |
| Import references | Drop files or use picker; choose sheet or separate views, optional HERO | Original bytes and hashes retained; image roles assigned explicitly |
| Detect/crop views | Inspect CV panel proposals and move crop rectangles | Accepted crop in source coordinates, no rewritten source |
| Calibrate | Mark axle centers/ground, enter known dimensions and provenance | Shared metric datums; locked authoritative measurements; uncertainty visible |
| Detect features | Optionally request body/wheel/edge/contour proposals | Proposals only, each bound to source/crop/provider revision |
| Correct in 2D | Points, splines, landmarks, measurements, semantic assignment | Accepted source observations; visible/inferred distinction retained |
| Check consistency | Compare all views, ratios, residuals and confidence | Current reference review or explicit source rejection before surface work |
| Construct cage | Create/edit a single shared world cage using constraints | Reprojection in all relevant views; individual critical checks pass |
| Inspect cage in 3D | Select a semantic entity in 2D/3D split | Named shared points/curves, no independent vehicle per view |
| Author patches | Assign boundaries/types/resolution/support/material | Valid bounded graph with unresolved edges shown; coarse preview labelled |
| Generate surfaces | Run existing stages through surfaces/silhouette | Current source/cage acceptance and headless gates required |
| Details and validation | Edit supported reusable components and inspect proofs | Normals/topology/pivots/roles/masks audited by core/Blender |
| Build / Render | Run or resume headless pipeline and watch logs | Four native result statuses; verified caches only |
| Manual review | Inspect required proof images and enter reviewer/notes/limitations | Standard hash-bound PASS or FAIL review; never inferred from execution |
| View/export | Inspect verified GLB; download/copy supported export | Exact artifact identity and freshness; downstream requirements separately checked |

The operator can stop, save, reopen and continue at any authoring step. A partial
draft is useful authoring data, not a successful build. Building is permitted only
through the readiness rules of the requested core stages. No invented positive
dimension, empty placeholder graph or fabricated PASS is used to satisfy them.

## New Vehicle wizard

1. Choose a name and a registered project location under an allowed root. The
   service derives safe IDs; names are display text, not paths or commands.
2. Choose a core profile such as sedan, coupe or wagon. Show required/optional
   roles from `profiles/`; do not infer dimensions from the category.
3. Import a combined sheet or separate FRONT/SIDE/REAR/TOP images and optional
   HERO/control overlay/surface target. Explain their distinct purposes.
4. Review panel detection. Assign roles, correct crop/rotation/display framing
   and mark missing views. Separate calibrated panels retain core priority.
5. Enter known length/width/height/wheelbase/wheel diameter where available.
   Unknown stays null in a validated draft. Units display in mm; core stores m.
6. Set provenance, source citation, authority class and uncertainty per measured
   quantity. A model or profile must never supply unverified OEM dimensions.
7. Review optional wheel-center proposals; mark ground/contact constraints.
8. Inspect initial calibration and shared axle lock in all four views.
9. Mark at least reliable greenhouse/pillar correspondences and run source
   consistency checks. A quick start may enter the editor with
   NEEDS_CORRECTION, but cannot enter accepted surface generation.
10. Open the editor with unresolved tasks and explicit draft/readiness state.

HERO supplies visual context unless a separate calibrated camera contract exists.
It must not appear as an accepted orthographic measurement or contribute an IoU
as if calibrated. Missing/ambiguous geometry is recorded, not filled with a
generic sedan guess.

## Three distinct decisions

| Decision | Vocabulary | Authority |
|---|---|---|
| Reference-authoring review | ACCEPTED / NEEDS_CORRECTION / INCONSISTENT_SOURCE | Explicit source review bound to current observations, calibration, provenance and limits |
| Pipeline stage result | PASS / FAIL / SKIP / BLOCKED | Existing headless gates; SKIP verifies cached outputs |
| Final visual review | PASS / FAIL | Existing `validation/review.json`, explicit reviewer and current hashes |

Reference ACCEPTED is necessary but insufficient for cage/surface or final asset
acceptance. Every critical landmark must pass individually. Confidence is a
ranking aid, not an error allowance. An author may correct a mistaken observation
with recorded reason and provenance; silently enlarging its tolerance or moving
world geometry differently in each view is forbidden.

## Mark II motivating case

At base `a3592f3`, the 2.730 m axle lock passes while SIDE/TOP A/B/C pillar spacing
is incompatible with the axle-locked affine interpretation. The rejected TOP
candidate needs 42.037 px / 244.170 mm correction between axles, 236.902 px /
1376.051 mm across the crop including untrusted extrapolation, RMS 73.163 px,
and local scale 0.518–2.150. It is **not active calibration**.

The intended Studio session loads the original sheet, marks axles/pillars, shows
the ratio conflict, highlights the TOP evidence, previews the candidate and
displays its excessive derivative range in red. Rejecting it records
INCONSISTENT_SOURCE and leaves active calibration/geometry untouched. The person
can replace a source as a new immutable reference or investigate correspondence/
projection. Surfaces remain blocked. Studio need not force every input to yield
a model.

This phase preserves Mark II cage FAIL, 44/66 original checks, surfaces/details
NOT STARTED and portability BLOCKED. See the unchanged
[source reconciliation report](../projects/mark2/validation/reference_reconciliation_report.md).

## Save, recovery and collaboration with existing tools

Manual Save commits a validated multi-document transaction. Autosave commits
valid authoring commands after an idle interval, while an incomplete property
entry/drag remains a recoverable unsaved edit. Named checkpoints snapshot
canonical files and source identities; restoring is a new validated transaction.
No Git commit/push is automatic product behavior. Git remains available outside
Studio; future Git UI needs its own explicit design.

External edits cause reload/compare/conflict UI. A current CLI/Blender build
freezes project writes under a shared lock; a user may continue local unsaved
drafting but cannot save it into that run. Closing the browser does not silently
kill a build. Reopening reconnects to job and recovery state. See
[transaction rules](studio_data_flow.md) and [locking API](studio_backend_api.md).

## Release acceptance scenarios

| Scenario | Observable acceptance |
|---|---|
| No AI/CV available | Import, calibrate, mark, edit, validate and build using manual tools; provider failure leaves all authored data intact |
| Original image preservation | Import/preview/crop/rectify/undo leaves original SHA-256 identical |
| 2D edit intent | Moving an observation cannot change cage XYZ; moving world XYZ updates all projected views |
| Cross-view failure | Select a failed semantic ID and see its evidence/residual/tolerance in every relevant view and 3D |
| Rejected warp | Save/reopen preserves rejection, original active transform and source bytes; Build cannot promote it |
| Scale provenance | Wheelbase shows value/unit/authority/source/uncertainty/lock; unknown data do not become guessed values |
| Undo/redo | A committed drag is one reversible command; split/merge changes bindings atomically; reload has no silent partial edits |
| External edit | A stale If-Match produces conflict rather than last-writer-wins overwrite |
| Dirty outputs | Editing cage visibly invalidates downstream artifacts/review through core dependencies |
| Build/review | All 14 stage results match CLI; stale/missing review blocks the same export in both paths |
| Mark II regression | No active data/evidence changes; INCONSISTENT_SOURCE is an accepted product outcome, not a valid asset |

## Scope exclusions and readiness

This architecture phase supplies documentation and contract examples only.
There is no production frontend, launcher, backend, CV model, game adapter or
optional UI spike. Final Class-A surfacing, arbitrary node scripting, browser
Blender, view-specific vehicle meshes, mandatory LLM services and automatic
review PASS are excluded. Inspection modes and provider/tool interfaces are
extension points, not implemented features.

The design has no blocking missing input. Production implementation is gated by
the generic core contract/locking/readiness work and measured browser performance
listed in the roadmap. Architecture review should confirm those tradeoffs before
a full frontend is built.
