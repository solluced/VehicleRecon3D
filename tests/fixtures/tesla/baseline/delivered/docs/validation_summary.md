# Final validation

Reference registration: **PASS with documented source inconsistencies**. Cage: **complete**, 53 semantic curves. Original five reference images verified unchanged. The normalized ratios and assumed 4.8 m scale are documented in reference_dimensions.md.

| View | IoU | Suggested threshold | Result |
| --- | ---: | ---: | --- |
| SIDE | 0.9572 | 0.94 | PASS |
| TOP | 0.9361 | 0.92 | PASS |
| FRONT | 0.9312 | 0.92 | PASS |
| REAR | 0.9447 | 0.90 | PASS |

These are actual opaque geometry renders from the fixed calibrated cameras, compared with manual source-image traces including tires and mirrors. No per-view bounding-box fitting is performed. End views use the declared reference rectification. Pixel mismatch and bounding-box deltas are in validation/report.json; colored comparisons are under validation/masks/ (red = reference only, blue = model only).

Surface review: **PASS for visual SubD presentation**, using studio, reflection-coordinate stripes and Workbench car-paint matcap. The review and proof hashes are recorded in validation/surface_review.json. This is not a numerical G2 certificate.

Topology: **99.81% quads**, with finite coordinates and no zero-area faces. See validation/geometry_audit.json. Wheelbase from actual wheel roots: **3.077763 m**. The evaluated body envelope is approximately 4.807 × 1.882 m, with roof height about 1.524 m above ground; the small difference from the chosen envelope comes from subdivision and surface roll.

GLB: **PASS**, 191 mesh nodes and 245,952 triangles including the topology overlay. Every exported node matches the evaluated Blender triangle count and world bounds within 0.1 mm. See validation/glb_geometry_report.json. The HTML embeds the exact GLB bytes, verified by SHA-256.

Viewer: **PASS** at 1440 × 1000 desktop and 390 × 844 mobile. Browser tests exercised all five presets, automatic framing, fit/reset, four layer toggles, mouse drag, wheel zoom and two-finger pinch. No WebGL errors were recorded. See validation/viewer_qa.json and viewer_desktop.png / viewer_mobile.png.

Scope limits: physical length is assumed; cross-view source conflicts are reconciled rather than concealed. Interior and lamp optics are simplified. Blender materials and browser lighting differ, while exported geometry is shared exactly. The saved model is a panel/SubD assembly, suitable for continued surface editing and presentation.

Required files, source/export hashes and the exact embedded GLB are checked by scripts/finalize_delivery.py. Local Git milestone history is retained; final working-tree status is checked after the delivery commit.
