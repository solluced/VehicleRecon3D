# Optional source-axis rectification

`CalibrationTransform` can rectify one raw image axis before applying its
existing affine plane basis. The inverse uses the same interpolant, solved by
bracketing; it does not interpolate the anchors in reverse. Geometry remains
in a single shared world space. The operation has no vehicle-specific behavior.

Each view may contain this optional calibration record:

```json
{
  "rectification": {
    "type": "piecewise_monotonic",
    "axis": "u",
    "image_domain_px": [400, 900],
    "affine_domain_px": [410, 910],
    "anchors": [
      {"image": 0, "world_normalized": 0, "semantic": "datum_start"},
      {"image": 0.5, "world_normalized": 0.51, "semantic": "roof_junction"},
      {"image": 1, "world_normalized": 1, "semantic": "datum_end"}
    ],
    "max_scale_change": 0.1
  }
}
```

The image domain normalizes raw source pixels. `world_normalized` denotes the
corresponding coordinate along the affine basis, normalized by the second
domain; it is not an independent 3D point. When those domains describe wheel
axes, exact 0/0 and 1/1 anchors lock their longitudinal world coordinates. Both
domains must increase. Either image axis is supported; the unselected raw pixel
coordinate is unchanged. Any existing affine in-plane shear still applies.

PCHIP uses weighted harmonic-mean interior derivatives and limited one-sided
endpoint derivatives, following the algorithm documented by
[SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.PchipInterpolator.html).
The implementation uses only the standard library, including in Blender.
Anchors must increase strictly on both axes. Standard PCHIP configurations with
zero endpoint/interior derivative are rejected: this calibration contract needs
a strictly positive derivative, including positive linear extrapolation tails.
Duplicate, reversed, nonfinite or incompletely normalized inputs are errors.

The exact quadratic derivative extrema on every segment are checked against
`1 +/- max_scale_change` (default 10%). This limit refers to local scale relative
to the axle/datum-normalized affine map, not raw pixels per metre. Large warps
are rejected when loading calibration. The lower-level interpolator can be used
to audit a rejected candidate; that does not authorize applying it. Extrapolated
regions remain hypotheses and need separate observations.

Blender references with an accepted warp use texture strips at most one source
pixel wide, with original-image UVs. Only reference geometry changes; the vehicle
does not acquire separate meshes or controls per view. No-rectification projects
retain the original four-corner reference planes and arithmetic. Silhouette
trace segments also use the shared transform and are subdivided on the nonlinear
axis before rasterization, resolving their curved boundaries.

Calibration bytes and implementation identity already participate in stage
cache keys, so changing anchors invalidates calibration and its dependents.
No cache-policy exception is introduced. Numerical success does not certify
source consistency: independent held-out landmarks, physical plausibility and
an explicit source review remain necessary. Store unaccepted candidates outside
the active `generated/calibration.json`; never lower image tolerances to fit them.
