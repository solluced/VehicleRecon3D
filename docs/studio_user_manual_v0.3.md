# VehicleRecon Studio v0.3 — annotation assistance

The [v0.2 manual](studio_user_manual_v0.2.md) still describes four-view editing,
correspondences, residuals, source/cage reviews, solver proposals and the 3D cage.
This release adds optional source-image assistance. None of the assisted tools
reconstructs a vehicle or accepts a review automatically.

## Start and availability

```powershell
python -m pip install -e . -e "studio/backend[cv]"
vehicle-recon studio --root F:/T/projects
```

The `cv` extra installs the deterministic local OpenCV CPU baseline. Installing
Studio without that extra, or launching with `--disable-cv`, leaves manual tools
available. The provider selector reports unavailable providers explicitly; it
does not silently substitute another provider. No models are downloaded, source
images are not sent to an external service, and operation needs no internet or
GPU. A failed, empty or cancelled operation leaves canonical data unchanged.

V2 drafts support source acceptance; v1 projects are read-only in Studio. Keep
the protected Mark II read-only: its source is INCONSISTENT_SOURCE, portability
BLOCKED, surfaces and details NOT STARTED. This release does not resume it.

## Proposals and source identity

`CV proposal ≠ source observation ≠ world geometry`.

Proposals live in a separate dashed purple transient layer. Accepted source
observations use the normal solid display. Stale proposals are orange; rejected
components are muted. View, exact image SHA, calibrated crop, canonical source
revision, provider version, parameters and input hash remain inspectable.

Changing source pixels, crop/framing, observation context or provider parameters
stales proposals. ACCEPT is disabled and the server rejects a stale acceptance.
RERUN creates a fresh result with current parameters. Reload an externally changed
project before rerunning. SIDE results cannot create observations in TOP.

Proposals, rasters and deterministic caches are disposable, tab-owned backend
memory. They may expire when their limits are reached or the server restarts.
Accepted observations carry self-contained provenance and do not need a cache.
Deleting or rejecting a proposal does not change a canonical review or revision.

## Smart Edge

1. Select Smart Edge in the source toolbar.
2. Click the feature's starting point.
3. Move along the expected feature. The yellow preview follows nearby contrast.
4. Click to commit a segment. Continue with more directed segments if needed.
5. Press Finish trace to inspect, simplify or fit the proposal.
6. Assign a semantic role, inspect the source and explicitly ACCEPT selected.

Use Weak / Normal / Strong for contrast. ROI / Advanced exposes a small set of
local search controls: radius, attraction, direction/smoothness and minimum
contrast. A path search is limited to 262,144 source pixels and 80,000 expanded
nodes. Commit shorter segments when a budget is exceeded. One click cannot trace
the whole car. Edges can follow trim, reflections or background; the operator
remains responsible for choosing the intended feature.

The Measured interaction timings panel shows preview and segment-commit p50/p95.
Preview measurements include coalescing/debounce, the local request and displayed
result. These measurements do not include canonical ACCEPT/save.

## Magic Select

Select Magic Select and drag an ROI at least 8 × 8 source pixels around the
desired region, leaving some background. The local GrabCut baseline proposes a
mask and independently addressable outer contours. It uses color/contrast,
without semantic vehicle understanding.

Use Foreground / Add region to paint included areas and Background / Remove
region to paint excluded areas. Choose the source-pixel brush radius. Each
stroke reruns the proposal with the accumulated FG/BG constraints; the source
image is never rewritten. Mask preview can be hidden independently of contours.
Narrow the ROI if the result includes background or exceeds the 4,194,304-pixel
segmentation budget. All painting remains inside the source-view crop.

Choose only the contours you want, assign their role and ACCEPT selected. Other
active components become stale after that canonical revision changes. Use REJECT
selected to discard unwanted components before acceptance. An outer silhouette
becomes source evidence, without creating a complete 3D cage.

## Detect Wheels and Trace Contour

Detect Wheels searches the chosen ROI for circle-like edges. The inspector lists
centres, radii, scores and candidates. Select a candidate explicitly; accepting
one creates a source circle/datum observation. Its circularity score is geometric
agreement, not the probability that an object is a wheel. Logos, round lights and
background objects can be candidates. No candidate moves a world axle centre.
Use existing correspondence/solver tools later for world interpretation.

Trace Contour returns independently addressable connected edge components.
Inspect the intended component and use Reverse direction, Trim contour and
Open/Close contour as needed. Reflections are still possible. Circle candidates
are confirmed as source circles; use manual source tools for subsequent edits.

## Simplification and fitting

EDIT / contour / fitting exposes source-pixel tolerance, maximum control points,
important-corner preservation and optional spline fitting. Simplify / Fit
proposal updates transient geometry only. Impossible point-budget/error-bound
combinations return an error instead of silently increasing error.

The inspector displays maximum/RMS sampled deviation, a continuous error upper
bound, original sample count and control point count. Overlay original contour
shows the untouched dense result alongside the edited/fitted proposal. Fit
metrics refer to the current working contour; intentional edits need inspection
against that original. Endpoints and requested important corners are preserved.

## Inspect, accept, reject and undo

The inspector shows provider/version, operation, source revision/crop,
parameters/input hash, current/stale status, geometric scores and fit evidence.
Component checkboxes control partial acceptance; the semantic role applies to
the selected components. UNKNOWN is the initial role and cannot be accepted.

By default accepted evidence remains INFERRED. Check “I verified these source
pixels” only after inspection to record measured/observed evidence. ACCEPT uses
the existing revision-checked typed transaction and invalidates affected source
and cage reviews. Undo restores the exact pre-accept canonical bytes; redo uses
the same core history. World geometry remains separate.

REJECT and EDIT before acceptance leave canonical state and reviews untouched.
Cancel CV job requests cooperative cancellation. An OpenCV native call must
return before cancellation finishes; CANCELLING is not completed cancellation.
Manual tools remain available while a provider is absent or has failed.

## Diagnostic and manual layers

Edge Map is an optional deterministic Canny diagnostic with visibility, opacity
and threshold controls. Update edge map computes it for the current ROI.
Changing parameters discards the displayed old diagnostic. It is not a semantic
probability map and never becomes canonical geometry.

Manual tools remains the exit from assistance. Point, Polyline, Spline, Landmark
and Measure use the current explicit profile semantic role. Landmark records a
source point. Measure records a two-point source axis and displays its pixel
length; it does not infer metres. Finish curve commits it. Zoom/pan/DPR and crop
transforms resolve to original source pixels for both manual and assisted tools.

No rectification editor, surface editor, Blender Render button, neural-model
download or Cyberpunk adapter is introduced. Release measurements and regression
evidence are in [validation/studio_v0.3](../validation/studio_v0.3).
