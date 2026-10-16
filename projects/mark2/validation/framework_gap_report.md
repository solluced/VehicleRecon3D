# Generic calibration gap: nonlinear illustrative-view rectification

Recorded before implementing the extension, 2026-10-16.

`CalibrationTransform` currently supports only a rank-two affine image-to-world
map. The calibration schema rejects any per-view rectification operation, and
Blender reference planes use just four corners. There is no suitable existing
nonlinear view operation. The previous cage-correction core freeze is superseded
for this narrowly scoped extension by the reference-reconciliation handoff.

AI-generated multiview references may preserve axle placement and outer bounds
while locally distorting longitudinal feature spacing. The independently
observed SIDE/TOP ratios in `view_longitudinal_ratios.json` fail an axle-locked
affine correspondence. This is a generic calibration limitation, not a missing
vehicle surface operation.

Proposed capability: `PiecewiseMonotonicAxisWarp`, a vehicle-independent,
strictly increasing cubic Hermite map on one normalized image axis, before the
existing affine plane map. Its inverse must be solved from that same interpolant.
Exact endpoint/axle anchors, positive derivative, linear endpoint extrapolation,
explicit local-scale limits and content-cache invalidation are required.
Distorted reference textures need subdivided geometry with original-image UVs;
the world-space vehicle geometry remains shared across all views.

No `mark2` branch or project-specific Python is permitted. Candidate calibration
data must stay separate from the active project calibration until accepted.
The generic numerical operation cannot certify that a synthetic source is
physically plausible. Extreme distortion is a source rejection, never an
automatic acceptance or a reason to weaken landmark tolerances.

All new numerical/schema/cache tests and a fresh full Tesla regression are
required before shipping the extension. Tesla identity/no-warp behavior must
retain its existing geometry, masks and acceptance policy.
