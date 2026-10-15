# Adding an automobile without project-specific Python

v0.1 is regression-tested on Tesla. This document describes the data workflow;
another vehicle has not been reconstructed in this release. Mark II is reserved
for v0.2 and was not consumed or modified during this implementation.

1. Create a project folder and put its inference images in input/.
2. Run `python -m vehiclerecon init projects/<id> --profile sedan` (or another
   supplied body family). It creates an authoring draft. Unmeasured dimensions
   are null; inspect/run reject it until the missing data are supplied.
3. Set metadata, reference paths, authorized/measured dimensions and provenance.
   Fill scene, materials, validation policy, semantic bindings, export/viewer
   settings. A profile describes roles, not coordinates or a stock-car shape.
4. Generate/edit calibration.json: image hashes/sizes, four affine maps, crops,
   uncertainty/rectification, ground and wheel landmarks, camera/plane settings.
   Use shared wheel geometry as the sole source for axle centers/tire radius.
   Check aligned proofs with `run --until calibration`.
5. Use overlay_raw.json only as annotation proposals. Generate/edit semantic
   world-space cage records and guides; validate the cage before dense surfaces
   with `run --until cage`.
6. Author surface_graph.json using the bounded operation vocabulary and named
   dependencies. Supply independent semantic boundaries, real arch geometry,
   panel/material roles and sampling/normal/support policies. Provide manual
   source silhouette observations. Run through silhouette; correct data on a
   failed gate. Do not weaken thresholds or fit each render independently.
7. Author details.json with parameterized components and declarative UV
   selections. Bind role IDs to actual outputs. Complete presentation settings,
   run the standard pipeline and inspect the real rendered proofs.
8. Record an explicit visual decision, including limitations, then rerun.
   Export and viewer use the accepted Blender model and exact verified GLB.

Use the Tesla JSON files as schema/operation examples; do not inherit its
geometry, dimensions or point coordinates for another vehicle. Calibration and
semantic authoring require geometric judgment. v0.1 does not automatically infer
a finished car from image pixels or promise perfect semantic CV extraction.

No `build_<vehicle>.py`, serialized lambda or vehicle-name branch is allowed.
If an operation is missing, first demonstrate that it is a reusable automotive
capability, implement it in the framework, cover it directly with tests and use
it through versioned project data. Stop on missing/ambiguous required sources.
