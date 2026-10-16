# Project format v1

`project.json` uses `schema_version: 1` and category `automobile`. Unknown
structural properties, unsupported versions, nonfinite coordinates and
non-positive physical dimensions are rejected. References use project-relative
POSIX paths. Absolute paths, drive/UNC paths, backslashes, parent traversal and
resolved escapes are forbidden. Required input/generated files must exist.

```text
projects/<id>/
  project.json
  input/                       original images
  generated/
    calibration.json
    cage.json
    surface_graph.json
    details.json
    silhouette_traces.json
    overlay_raw.json           unclassified color proposals
  validation/                  masks, reports, proof images, review.json
  output/                      blend, GLB, viewer and delivery manifest
  .cache/                      stage entries/checkpoint blends; not distributed
```

| Owner | Authoritative content |
| --- | --- |
| project.json | Identity/profile, dimensions and provenance, file locations, materials, scene/presentation, semantic bindings, export/viewer policy and validation thresholds. |
| calibration.json | Source image hash/size, four affine bases and observed landmarks, crops, rectification/uncertainty, cameras, reference datums and shared wheel geometry. |
| cage.json | Calibrated world-space rails/sections, symmetry, semantic IDs, landmarks, and wheel/arch templates referencing the shared axle records. |
| surface_graph.json | Named operation nodes/dependencies, patch boundaries/resolutions/materials/support rows, final boundary stitch, blockout wheel/liner settings. Tire radial profiles are normalized against the shared wheel radius. |
| details.json | Bounded component operations and parameters: UV intervals, splits, masses, wheel profiles/spokes, curves and paired surface attachments. |
| silhouette_traces.json | Manual observations in the source-image coordinate system; not a generic automobile silhouette. |
| review.json | Explicit reviewer decision, geometry/input hashes, proof hashes, notes and limitations. |

Calibration is an affine map from image `(u,v)` to a declared world plane,
optionally preceded by a [monotonic source-axis rectification](reference_rectification.md).
`world_to_pixel` intentionally discards invisible depth. SIDE/TOP/end-view
envelopes must agree with project dimensions and shared axle wheelbase.
End-view anisotropic rectification is retained explicitly, not hidden by fitting
each rendered mask. Separate images take priority when supplied and must match
their declared calibrated panel framing; update calibration for another framing.
PNG/JPEG bytes are detected independently of the filename extension.

Surface operations: polyline, chord_hermite, shape_preserving_hermite,
bezier_rail_range, curve_sample, lerp, offset, coons, cubic_boundary_roll,
arch_annulus, ribbon, bilinear_patch and boundary_stitch. Missing IDs, cycles,
invalid schedules, unsupported operations and disagreeing Coons corners fail.
Component selections use strict lower/upper UV intervals; null means unbounded.
No JSON field is executed as Python.

Schemas are installed with the package as shared resources. Structural schema
validation is complemented by semantic checks for dimensions, paths, graph
references, role bindings, symmetry/cardinality and geometry. Profile floors
cannot be weakened by a project's threshold settings.
