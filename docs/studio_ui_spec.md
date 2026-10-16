# VehicleRecon Studio interaction specification

Status: proposed behavior and acceptance criteria; no production UI in this
phase. Coordinate/persistence rules are defined in [data flow](studio_data_flow.md).
API examples are in [backend API](studio_backend_api.md).

## Workspace responsibilities

```text
Project | Reference | Cage | Surfaces | Details | Validate | Run
Views/layers        Main 2D editor or side-by-side panes        Properties
FRONT SIDE REAR TOP  original reference + independent vectors   Semantic role
HERO (context)      crop/observation/world-edit mode indicator  Coordinates
                    selection shared across panes             Constraints
2D / 3D split       live cage or current verified GLB           Provenance
                    Validation, conflicts, pipeline and logs   Confidence
```

The left rail owns view selection, layer visibility/order and object discovery.
The center owns spatial interaction. The inspector shows only fields relevant
to selected entities, including original pixels, world metres, provenance and
edit intent. The bottom panel owns actionable failures and build progress. A
project bar always shows revision, unsaved count, save/conflict state and last
build identity. Pages share one selection and command history; switching pages
does not reinterpret coordinates or accept a proposal.

Default working mode is 2D/3D split with a selected source and live shared cage.
Side-by-side source panes and a four-view overview are available. Each pane has
its own viewport; selecting an entity focuses its counterparts without moving
the user's zoom unless Focus All is invoked. The right pane can show the latest
built GLB, with its revision and stale flag, instead of a draft cage.

## Viewport navigation and image identity

Smooth wheel zoom anchors the same source pixel under the cursor; zoom never
changes observations. Space+drag or middle-button drag pans. Fit centers the
declared panel; 1:1 means one source pixel per device pixel, with CSS/device-pixel
ratio stated. Keyboard +/- zooms, arrows pan, F fits, 1 selects 1:1, Escape
cancels the current gesture. Fullscreen uses the browser capability and has a
visible exit. Navigation does not enter geometry undo history.

Optional synchronized zoom uses pixels-per-screen-unit for pixel inspection or
metres-per-screen-unit only when both views have accepted calibration. It does
not stretch unlike views to appear consistent. Crop-local, full-sheet, rectified
and screen coordinates remain distinct. The inspector always provides the
original full-source pixel location, including when inspecting a rectified
preview. Axis/crop transforms are explicit and reversible.

Support keyboard view switching, focus traversal and equivalent toolbar actions.
Source and layer opacities change compositing only. Authored vectors remain
separate from source bytes. Display color/EXIF orientation transforms are tracked
in the view adapter; observations refer to the defined decoded-source frame.
HERO is labelled UNCALIBRATED CONTEXT unless a supported camera is available.

## Layer contract

Every layer exposes `visible`, `locked` and `opacity` (0..1). Locking prevents
selection edits but not inspection; generated layers are read-only. Layer UI
preferences are session state, never build inputs. Source bytes have a permanent
content lock. Hiding a failed layer does not remove its checks.

| Layer | Content / interaction | Default ownership |
|---|---|---|
| SOURCE IMAGE | Immutable reference, crop frame, opacity | Canonical image identity; display state local |
| AUTO BODY MASK | Segmentation proposal with confidence and accept/reject | Provider proposal, read-only raster |
| AUTO EDGES | Edge probability or gradients | Disposable provider output |
| CONTROL POINTS | Accepted editable vector handles | Source observation or world geometry, explicitly selected mode |
| VISIBLE SPLINES | Blue solid observed feature curves | Source observation vectors |
| INFERRED SPLINES | Red dashed hidden/uncertain feature hypotheses | Explicit inferred provenance, never measured evidence |
| DATUM / AXES | Green ground, centerline, axle and scale anchors | Shared calibration constraints; authoritative locks shown |
| LANDMARKS | Named source observations and distinct projected markers | Separate observation and geometry identities |
| MEASUREMENTS | Pixel/physical lengths, angles, provenance, uncertainty | Canonical measurement records |
| SEMANTIC CAGE | World rails/sections and their projections | Core-authored geometry, core sampling |
| VALIDATION PROJECTION | Projected world points/curves, residual arrows | Derived, revision-bound, read-only |
| RESIDUAL HEATMAP | Normalized error and conflict focus targets | Derived, read-only; color plus text/icons |
| RECTIFICATION PREVIEW | Candidate mapping and corrected image placement | Explicit candidate-only toggle; active transform separately labelled |
| SURFACE BOUNDARIES (optional) | Patch edges and assignments | Canonical graph selection |
| PATCH PREVIEW (optional) | Coarse colored patches | Core-derived feedback, not final acceptance |
| TOPOLOGY PREVIEW (optional) | Actual mesh edges of a built artifact | Blender-derived; no decorative fake wire |

Keep overlay colors distinct from result indicators: inferred red dashed splines
carry a hypothesis icon, while failures use numbered arrows/badges and table
rows. Color is never the only distinction. Dense controls may hide labels at low
zoom while retaining picking and the accessible entity list.

## Tool lifecycle and editing intent

Tools implement `activate`, pointer/key handlers, `preview`, `commit` and
`cancel`. They emit typed commands, not mutations of Konva/Fabric objects saved
as project JSON. The command layer checks locks, capability/schema support,
bindings and edit revision. Each drag is one undoable command; Escape restores
its start value. Future tools register capability IDs and compatible commands.
They do not extend geometry schemas merely to add an interaction gesture.

| Tool | Gesture / result | Canonical intent |
|---|---|---|
| Select | Click, additive select, marquee, entity-list navigation | Session selection; no geometry mutation |
| Move | Drag with optional axis/plane lock | Explicit MoveObservation or MoveWorldLandmark |
| Add Point | Click on selected curve/segment | Insert stable source/geometry point and update bindings atomically |
| Delete Point | Delete selected unlocked point | Dependency preview; reject unresolved/minimum-cardinality result |
| Polyline | Click vertices, Enter completes | Editable source contour or declared world section |
| Bezier / Spline | Place/edit knots, drag tangents | Accepted source vector; world tangent editing requires supported core handle contract |
| Smart Edge | Start, follow boundary, commit segments | Editable observed vector proposal; see below |
| Magic Select | Seed points/box, refine selection | Optional CV mask/contour proposal; explicit acceptance required |
| Landmark | Name a source feature and link shared identity | Observation with semantic/world correspondence |
| Measure | Two points/circle/angle construction | Measurement with units, provenance and uncertainty |
| Wheel Circle | Fit rim/tire silhouette, choose what diameter means | Pixel proposal; metric radius only after scale/measurement acceptance |
| Wheel Arch | Mark opening and supporting boundary | Source curve then shared real arch geometry; no painted hole |
| Section | Choose station/plane, edit cross-section | World section under core cage contract |
| Symmetry | Enable/edit a shared symmetry relationship | Core side-sign expansion; observations remain individually observed |
| Mirror | Preview and commit canonical symmetric entities | New linked core entities, no per-view vehicle copy |
| Constraint | Select datums, axes, distances, correspondence | Supported core constraint operation; unresolved depth stays unresolved |
| Semantic Assign | Pick profile role and feature qualifier | Existing role + canonical object/landmark binding |
| Rectification Anchor | Pick correspondence, edit normalized pair | Candidate calibration only until explicit acceptance |

The mode indicator must distinguish **Edit source observation** from **Edit
shared world geometry**. In observation mode, a 2D drag changes only a measured
pixel/vector and invalidates its review. In world mode, a 2D drag needs an
explicit movement plane/axis, a fixed depth or supported multi-view constraints.
A single rank-two view cannot determine invisible depth. Show constrained DOFs
and refuse an underdetermined move rather than silently invent depth or a second
point for another view. A symmetric instance move is converted back to the one
canonical point and reprojects both sides.

World geometry uses metres; inputs may display mm. A tolerance edit is a policy
change with provenance and review invalidation, not a shortcut button beside a
failed residual. Profile floors and authoritative locks remain enforced by the
backend/core. Features unsupported by the current document version are disabled
with a reason or offered through explicit migration, never saved as unknown keys.

## Automotive palette and stable identity

Load required/optional roles from the active core profile. Palette groups are
navigation presets, not a second ontology. Feature qualifiers and display labels
identify subfeatures within a role; they do not add arbitrary profile roles.

| Palette | Core mapping |
|---|---|
| BODY: centerline | Calibration datum / symmetry axis |
| hood_center, hood_shoulder | `hood` role; qualifier on named rails/boundaries |
| fender_crown | `front_fender` or `rear_quarter`, with station/side qualifier |
| beltline, shoulder_character | Named cage rails with the owning panel role |
| rocker_upper, rocker_lower | `rocker` role and rail qualifier |
| GREENHOUSE: windshield, roof_edge/center, window_sill | `windshield`, `roof`, corresponding panel/rail bindings |
| A/B/C pillar, rear_glass | `a_pillar`, `b_pillar`, `c_pillar`, `rear_glass` |
| PANELS: hood, front/rear door, trunk/hatch, bumpers | Exact corresponding required/optional profile roles |
| WHEELS: axle_center, tire_radius, wheel_arch | Calibration `wheel_geometry`, `wheel` and `wheel_arch` roles |
| DETAILS: headlight, taillight, mirror | Core profile roles and supported detail component records |
| intake | Labelled detail-component preset using bounded `cavity`/`attach` operations; no invented required profile role |

`A_PILLAR_ROOF_L` is a displayed shared landmark instance, not a role string
added to `profiles/`. Stable IDs and atomic split/merge binding rules are specified
in [data flow](studio_data_flow.md#identity-and-proposed-core-authoring-contract).

## Smart Edge, Magic Select and fitting

Smart Edge starts with a committed seed. Pointer motion searches a bounded ROI
near the intended feature using normalized gradient/edge probability, local
contrast, optional segmentation boundary and path smoothness/distance costs.
An incremental shortest-path search may supply candidate segments; the exact
algorithm belongs to the provider/tool service, not the reconstruction engine.
No snap crosses locked features or gaps beyond configured search limits without
an explicit inferred segment. Display confidence and alternative paths; the
person can place another seed, bypass the snap or undo the last segment.

Commit produces an editable dense source contour with source/provider provenance.
Fitting then applies simplification and bounded spline fitting. Expose source-pixel
fit tolerance, smoothing, maximum points and corner preservation; show maximum
deviation against the original contour. Fitting error is separate from semantic
reprojection tolerance. Accepting a fit never increases validation tolerance.
Changing fit settings previews a proposal; Commit replaces the selected source
vector as one command. Add/remove/move points, change tangents, split/merge curves
remain available, with preserved semantic IDs and explicit rebinding on deletion.

Magic Select offers positive/negative seeds and bounding boxes only when a
provider advertises them. Empty/low-confidence/disconnected results remain
proposals. The manual polyline/landmark workflow is always available.

## Correspondence, consistency and conflict panel

Selecting a semantic entity highlights its source observation, projected world
location, owning curve/patch and 3D point in every relevant view. A table shows
original reference pixel, projected pixel, dx, dy, Euclidean residual, tolerance,
confidence/provenance and individual PASS/FAIL. Occluded/unobserved features are
labelled unavailable and are never manufactured from the projection itself.

Use normalized residual `rho = residual_px / tolerance_px`: green `rho <= .8`,
yellow `.8 < rho <= 1`, red `rho > 1`, grey for unavailable/stale evidence. These
are visual bins; the actual per-landmark test remains `rho <= 1`. Lists retain
all failures, not only averages. Click a row/heatmap marker to focus all panes.

The Reference Consistency panel shows locked wheelbase/axle/ground alignment,
silhouette landmarks, longitudinal pillar ratios, cross-view residuals and full
uncertainty intervals. It separates source observations, calibration hypotheses
and current geometry. An affine incompatibility certificate explains which
correspondences fail; it does not claim every perspective model is impossible.
Source review offers ACCEPTED / NEEDS_CORRECTION / INCONSISTENT_SOURCE, with a
reason and current hash bindings. The source/cage gate is enforced headlessly
before surfaces, once the proposed core extension is implemented.

## Rectification workspace

Show original and preview views plus mapping and derivative/local-scale graphs.
Edit sparse trusted source/target-normalized anchors with their semantic IDs;
front/rear datum anchors are locked. Adding/removing an anchor changes only a
candidate. Display source coordinate, rectified coordinate, monotonicity,
minimum derivative, scale extrema, RMS and maximum pixel/physical correction.
Separate measured/anchored regions from extrapolated tails in graphs and image.

The Preview toggle only controls visualization. It never enables the candidate
in `generated/calibration.json`. The backend diagnoses candidates with the
lower-level core interpolator and checks acceptance with `AxisRectification`.
Non-monotone, duplicate, zero-derivative or excessive-scale candidates show the
precise core error. The 10% current limit is shown; no automatic override exists.
Accepted limits remain project/core policy and are unchanged by this phase.

Accept requires a current diagnostic result, provenance, independent held-out
checks and explicit user intent; it activates calibration transactionally and
invalidates downstream evidence. It does not PASS the cage. Reject retains the
candidate and decision for inspection while leaving active calibration untouched.
Reopening a rejected candidate restores that distinction. The Mark II range
0.518–2.150 must be red, remain rejected and keep surface generation blocked.

The candidate image preview is read-only derived display data. Place/edit source
observations and anchor picks in the original pane; the backend supplies inverse
source-coordinate inspection for a preview. Browser code does not implement a
second PCHIP solver to guess an editable source pixel in the warped display.

## Graph, quality, settings and build workspaces

The surface editor offers patch creation, boundary pickers, bounded operation
type, dependency links, sample resolution, mirror, material, support rows and
supported continuity constraints. Boundary orientation/corner agreement and
unresolved IDs appear before build. It has no arbitrary script node. G1/G2
certification is not implied by a Coons patch; unsupported continuity checks are
identified as future core capabilities. Preview patches use core sampling.

Wireframe, normals, curvature, reflection/zebra, patch boundaries and topology
density are inspection-mode extension points. Final topology wire uses actual
Blender mesh edges; source splines/control polygons have separate names/styles.
Curvature/zebra may be diagnostic without proving automotive Class-A quality.

Schema-generated inspectors consume canonical types, enums, bounds, descriptions
and optional labels/units/groups/advanced metadata. Widget overrides handle
points, references and boundaries, without changing the persistence contract.
Normal controls prioritize visual actions. Advanced groups expose sampling,
interpolation, support rows and declared calibration limits with provenance.

The Validate page displays fixed-camera reference/model/difference masks, IoU,
semantic residuals, report revision and clickable failure regions. The review
screen shows all required proof images, geometry hash, current input hash and
limitations. The user enters reviewer/note/limitation and explicitly selects
PASS or FAIL. Studio uses the standard review operation; it never auto-PASSes.

The Run page lists all 14 core stages. A separate activity badge may say waiting
or running while `result` is absent; completed results remain exactly PASS,
FAIL, SKIP or BLOCKED. Missing/stale review remains blocking. Build / Render
invokes the core pipeline through a local job; no Blender work runs in-browser.
Show stdout/stderr as text, cancellation and last stable artifact identities.
Load a new GLB only after export and GLB verification pass for the current run.

## Performance and accessibility

Targets are budgets to validate, not measurements achieved in this phase. Test a
documented 4K (3840x2160) source with 5,000 editable points, 20 vector layers,
four source panes and a cage split on a declared reference workstation/browser.

Initial manual-editor support targets maintained desktop Chrome/Edge and
Firefox, tested at device-pixel ratios 1, 1.5 and 2. Probe Canvas/graphics
capabilities at startup; 3D unavailability leaves 2D authoring/data inspection
usable with an explicit unavailable-preview message. WebGPU is optional and
never a baseline manual-editor requirement. Safari/mobile authoring expansion
needs its own performance/input validation rather than assumed parity.

| Interaction | Initial target / measurement |
|---|---|
| Pan/zoom and local drag feedback | p95 frame <=16.7 ms on active pane; degraded mode remains usable at 30 fps |
| Source/world edit to all-view diagnostic feedback | p95 <=100 ms on loopback, tagged with draft sequence |
| Picking | p95 <=8 ms with spatial index; screen-space handle tolerance independent of zoom |
| Command commit + local validation | p95 <=200 ms for a single-point edit, excluding Blender |
| First editor display | <=2 s after local image decode/cached project load; measure decode separately |

Use immutable committed snapshots, mutable gesture scratch buffers, per-layer
dirty redraw and requestAnimationFrame. Keep large masks/static sources out of
hit graphs. Reuse image bitmaps, cache a disposable resolution pyramid, cull
offscreen shapes and pool handle objects. Virtualize entity/conflict/log lists.
Coalesce backend preview requests to at most 20 Hz, cancel obsolete work and
discard stale sequence/revision replies. Pointer feedback stays local at frame
rate; pending diagnostics are labelled, not falsely current. Use workers for CV
and dense contour fitting. Release textures/listeners/workers on view close and
handle graphics-context loss by reloading canonical data.

Provide keyboard-accessible inspectors, entity lists, move/nudge actions,
visible focus and non-color failure cues. Pointer capture avoids accidental
mid-drag edits when leaving the canvas. Confirm destructive dependent deletions
with a concrete dependency preview; ordinary reversible drags use undo rather
than repeated modal confirmations.
