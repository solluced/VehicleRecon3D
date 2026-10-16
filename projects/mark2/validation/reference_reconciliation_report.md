# Reference reconciliation — stopped at source rejection

**REFERENCE SOURCE: INCONSISTENT.** The TOP-to-SIDE monotonic candidate is
rejected for excessive distortion. No accepted reference rectification exists.

The independent [longitudinal audit](view_longitudinal_ratios.md) compares 13
semantic rows, with the cowl/A-base alias counted only once as evidence. Both
axles determine the unique longitudinal affine transform. A/B/C roof spacing
cannot be reconciled under that transform and the full declared uncertainty.
SIDE is a provisional longitudinal gauge; the measurements demonstrate relative
non-affinity, not which view is independently true. Other perspective or
correspondence explanations remain open.

The [sparse PCHIP candidate](rectification_candidate.json) fits only two axle
datums and three near-side roof junctions. Its derivative is positive and C1,
but local normalized scale spans **0.518262–2.150012**, exceeding the 10% limit.
Even the most favorable full A-to-B uncertainty requires **16.04%** average
compression, so changing spline tuning cannot produce a modest accepted warp.

| Source correction | SIDE | TOP rejected candidate |
|---|---:|---:|
| Maximum between axles | 0 | 42.037 px / 0.089440 WB / 244.170 mm |
| Maximum across full crop | 0 | 236.902 px / 0.504048 WB / 1376.051 mm |
| RMS, 12 unique landmarks | 0 | 73.163 px |
| RMS, landmarks between axles | 0 | 27.249 px |
| Local longitudinal scale | 1 | 0.518262–2.150012 |

The full-crop maximum includes untrusted overhang extrapolation; it is not a
measured body dimension. All definitions, per-landmark displacements and the
uncertainty certificate are in [the magnitude report](rectification_magnitude.md).

The [generic gap](framework_gap_report.md) was documented before implementing
`PiecewiseMonotonicAxisWarp`. The extension adds optional per-view calibration,
the inverse of the same interpolant, strict derivative/scale checks, actual
subdivided texture planes and nonlinear trace sampling. No vehicle-specific
branch or project Python was added. Original identity/no-warp behavior remains.

Full tests: **149 passed**, including real Blender and installed-wheel tests.
The isolated cold Tesla reconstruction passed **all 14 stages**. Existing review
hashes verified against fresh renders; no replacement review was fabricated.
The [regression evidence](tesla_rectification_regression/summary.json) records:

| Tesla IoU | Exact fresh result |
|---|---:|
| SIDE | 0.957230 |
| TOP | 0.936083 |
| FRONT | 0.931202 |
| REAR | 0.944724 |

All explicit-review renders are byte-identical. Frozen cage controls/handles
match exactly; maximum frozen physical-control delta remains 1.1921e-7 m under
the existing 1e-5 m tolerance. Current exported positions, normals, triangle
indices and GLB JSON are identical. Seven UV accessors vary by at most one
float32 ULP (5.96e-8), so fresh GLB/viewer bytes differ; no metric, geometry or
image tolerance was changed. Published Tesla artifacts and frozen fixtures
remain untouched.

Mark II active calibration, cage, surface graph, details, images, project policy
and corrected Blender checkpoint are byte-identical to commit `b51b372`.
Wheelbase remains **2.730 m**, axle X **-1.365/+1.365 m**, ground Z **0**.
Stock L/W/H **4.760/1.755/1.400 m** remain provenance, and the drift-kit outer
envelope remains inferred. Project-specific Python: **0**.

Steps 12 and 13 require accepted rectification. Neither runs after this source
rejection: no `cage_*_rectified.png` files or post-rectification 66-row result are
claimed. For reference, the unchanged **pre-rectification** cage remains:

| Critical check | Original residual |
|---|---:|
| Passed / total | 44 / 66 |
| Maximum / mean | 52.273 / 10.397 px |
| A roof SIDE / TOP | 0.233 / 52.273 px |
| B roof SIDE / TOP | 0.000 / 29.243 px |
| C side roof SIDE / TOP | 0.000 / 43.149 px |
| C rear roof SIDE / TOP | 1.553 / 38.491 px |
| A group maximum SIDE / TOP, including attachments | 32.680 / 52.273 px |
| B group maximum SIDE / TOP, including attachments | 22.879 / 29.243 px |
| C group maximum SIDE / TOP, including attachments | 23.103 / 43.149 px |
| Front door leading edge | 32.680 px |

**CAGE: FAIL. SURFACES: STILL NOT STARTED. DETAILS: STILL NOT STARTED.**
**PORTABILITY: BLOCKED.** Continue only with consistent source views or an
independently justified correspondence/projection model; do not alter the shared
3D cage to absorb these source contradictions.
