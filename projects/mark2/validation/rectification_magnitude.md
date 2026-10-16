# Rectification magnitude and source decision

**REFERENCE SOURCE: INCONSISTENT. Candidate rejected; active calibration unchanged.**

SIDE is retained as the provisional longitudinal gauge; the data establish relative non-affinity, not independently known optical truth for either view. TOP is the candidate affected source view. The sparse fit uses only front/rear axles and A/B/C near-side roof corners. Other observed landmarks are held out.

| Quantity | SIDE | TOP candidate |
|---|---:|---:|
| Maximum correction between axles | 0 px | 42.037 px |
| Maximum normalized WB correction, between axles | 0 | 0.089440 |
| Physical equivalent, between axles | 0 mm | 244.170 mm |
| RMS correction, 12 unique landmarks | 0 px | 73.163 px |
| RMS correction, landmarks between axles | 0 px | 27.249 px |
| RMS correction, five fit anchors | 0 px | 25.834 px |
| Local longitudinal scale | 1.000 | 0.518262 to 2.150012 |
| Whole-crop maximum, including untrusted extrapolation | 0 px | 236.902 px / 1376.1 mm |

Corrections are source-normalized displacement times the TOP 470 px wheelbase or the authoritative 2730 mm wheelbase. They are not residuals. The full-crop number is dominated by untrusted linear overhang extrapolation and must not be represented as measured vehicle geometry. RMS includes held-out landmarks; the cowl/A-base duplicate is counted once.

The derivative is positive and continuous, but the normalized local scale spans 0.518–2.150. This needs roughly 48.2% local compression and 115.0% expansion, far above the 10% warning/acceptance limit. The runtime correctly rejects this candidate.

Independently of the interpolation choice, full A–B span uncertainty implies at least 16.04% average compression in TOP relative to SIDE. Therefore a modest +/-10% source-axis warp cannot solve the measured correspondence. Merely smoothing the spline cannot remove this lower bound.

The 2.730 m wheelbase, -1.365/+1.365 m axle X, ground Z=0, active calibration, cage, surface graph, details and all landmark tolerances remain unchanged. There is one world-space car. No warp is fitted to every noisy control point.

Step 12 requires accepted rectification. Because this candidate is rejected, no accepted rectified cage images or post-rectification 66-row review are generated. Existing pre-rectification results remain 44/66, max 52.273 px, mean 10.397 px; they must not be relabelled as rectified results. No geometry correction, surfaces or details follow.
