# Multi-view landmark fitting and diagnostic math

`vehiclerecon.authoring.fitting` is a pure NumPy/core service. Studio supplies
typed observations and displays its proposal; it never ports calibration math
to JavaScript. Canonical observation/world data and acceptance contracts stay
in schema family 2. No image recognition or invisible-depth heuristic is used.

## Projection and constraints

For each view, its calibrated origin `o` and basis columns `u,v` form `B`.
The affine projected coordinate is `B⁺(X−o)`. The existing
`CalibrationTransform.world_to_pixel` then applies the inverse of any active
one-axis rectification to obtain **original source pixels**. A correspondence's
declared Y instance sign is applied before projection. Rejected candidates are
never active transforms.

Exact constraints are world axis values or planes `n·X=d`. An SVD produces a
particular solution `X₀` and null-space basis `N`, so `X=X₀+Nq` satisfies those
constraints throughout the fit. Inconsistent exact constraints are rejected.
An explicit plane placement intersects the calibrated pixel ray with that
plane; a parallel ray returns an underdetermined error, never guessed depth.

The weighted projected design is checked for full rank on the unconstrained
coordinates. Singular values, rank, free dimension count and condition number
are reported. A relative singular-value threshold of `1e-10` and maximum
condition number `1e8` identify ambiguity. One unconstrained 2D observation is
always underdetermined. A single observation with an independent explicit plane
can determine a point; parallel multi-view evidence still cannot.

## Robust fit and acceptance

The deterministic affine/rectified least-squares solution initializes raw-pixel
Huber IRLS/Gauss–Newton (40 iterations maximum, backtracking line search). The
two-coordinate residual is normalized by declared uncertainty and optional
positive weight: `sqrt(weight)/max(uncertainty_px,0.25)`. The 0.25 px numerical
floor prevents zero uncertainty from becoming infinite weight. Huber transition
is 1.345 normalized residual units. Jacobians use centered world-coordinate
differences of `1e-6 m` through the shared projection service. The affine model
is exact; the rectified objective continues to use original raw pixels.

Unavailable, unmeasured/inferred and explicitly excluded observations are listed
with reasons, never silently counted as independent evidence. Bound source
knots retain their stable knot IDs. All included observations remain in the
individual report even if robust weighting reduces their influence. RMS,
maximum, projected pixels, dx/dy, residual and each declared tolerance are
reported. Any included residual exceeding its own tolerance marks the proposal
FAIL. A low mean cannot override a critical failure. Applying a visibly failed
proposal is an explicit authoring act, not acceptance of source or cage evidence.

## Proposal fencing

No solver call writes canonical files. The adapter retains at most 32 proposals
for five minutes, bound to project, authenticated tab and exact revision.
Apply uses a server-retained XYZ and one typed Add/MoveWorldLandmark command.
A different revision, expired proposal or another tab cannot apply it. Browser
changes/conflicts clear the ghost preview. Undo/redo is the shared core history.

## Residual heat and automotive diagnostics

The shared core report declares its heat policy: `residual/declared_tolerance`.
PASS is below 0.8; NEAR is 0.8 through 1 inclusive; FAIL is above 1; missing
evidence is UNKNOWN. The 0.8 warning band is a presentation policy; the individual
canonical tolerance and review gates are unchanged. All states have text labels.

SIDE/TOP longitudinal diagnostics normalize observed raw u between the same
projected front/rear axle datums. The ratio difference is compared with the sum
of declared pixel tolerances divided by each view's axle span. This is a
diagnostic comparison in raw source space, not a replacement for calibrated
projection or a rectification solve. Historical v1 evidence can provide its
previously audited uncertainty intervals instead. Neither path changes geometry.

Summary groups categorize existing semantic names for display only; they are
not a second authoring ontology or acceptance gate. Silhouette alone never
establishes consistency. Source acceptance and cage acceptance remain separate
explicit reviews, with inspected subject/proof identity, reviewer and note.

Three.js draws core-provided samples and labelled approximate AUTO control
polygons. It owns camera/ray picking/gizmo interaction only. Its world axes are
X longitudinal, Y lateral and Z up. Symmetry is displayed from declared cage
semantics; no frontend-only authoritative mirror edits are invented.

Primary implementation references: [NumPy least squares](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html),
[Three.js TransformControls](https://threejs.org/docs/pages/TransformControls.html),
[Three.js OrbitControls](https://threejs.org/docs/pages/OrbitControls.html).
