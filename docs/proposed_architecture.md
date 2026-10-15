# VehicleRecon3D v0.1 proposed architecture

Status: proposed for the extraction phase; no framework implementation in this
audit cycle. Boundaries follow the VehicleRecon3D handoff. Automobiles only.
Tesla remains the sole integration regression. No new vehicle is generated.

## Package and ownership

`vehiclerecon` owns algorithms. `projects/<id>/` owns every vehicle-specific
coordinate, patch binding, dimensional assumption, reference observation,
detail setting and visual review. `profiles/` owns semantic automotive grammar,
without geometry. `schemas/` owns versioned contracts. `tests/fixtures/tesla/`
owns immutable acceptance evidence and the delivered source identity.

| Package | Responsibility |
| --- | --- |
| `core/project.py` | Load schema_version=1 project, resolve paths within project root, resolve profile/data references, validate finite dimensions and input availability. No bpy import. |
| `core/pipeline.py` | Ordered stage dependencies, required gates, subprocess results and PASS/FAIL/SKIP/BLOCKED records. |
| `core/cache.py` | Deterministic content hashes of declared inputs, dependency digests, implementation version and existing outputs. |
| `core/manifest.py` | Output identities, provenance and safe delivery file enumeration. |
| `core/errors.py` | Typed schema, missing-input, reference-resolution, gate and Blender errors; CLI nonzero on required failure. |
| `reference/{calibration,transforms,panels,overlay_extract}.py` | Pure affine mappings, source selection/crops, landmark validation and initial color annotation extraction. |
| `cage/{schema,curves,sections,builder}.py` | Resolve point/curve records, symmetry, semantic sections, Blender curve creation. |
| `surfaces/{curves,coons,patches,topology,builder}.py` | Pure interpolation, typed boundary graph, sampling/support rows, mesh generation and explicit cleanup. No Tesla identifiers. |
| `details/{wheels,wheel_arches,doors,glass,mirrors,lights,bumpers,intakes,interior}.py` | Parameterized automobile components, UV-region cavities, geometric openings, normal/symmetry handling and evaluated-surface attachments. |
| `validation/{render,silhouette,geometry,report}.py` | Real fixed-camera renders, traced-mask IoU, read-only geometry audit and explicit review records. |
| `export/{glb,fbx,verify}.py` | Selection policy, format output and evaluated geometry verification. FBX is an explicit capability with availability checks; current Tesla has no FBX implementation to extract. |
| `viewer/{builder.py,viewer_template.html}` | Verified exported GLB embedding, metadata and camera config; model coordinates come exclusively from GLB. |
| `blender/{runner,scene,collections,materials,cameras}.py` | One executable discovery/startup path and shared bpy helpers. `--python-exit-code 1` mandatory; algorithmic modules do not start Blender. |
| `cli.py`, `__main__.py` | `run`, `init`, inspection and selected `blender build/validate/export` entry points using the same stage runner. |

Pure math and schema modules must import under ordinary Python. Only Blender
adapters import bpy. Add `blender/` to the proposed tree because the requested
common startup/scene helpers need a single explicit owner; it does not move
vehicle data into the framework.

## Data contracts and schemas

Use JSON Schema Draft 2020-12 with required fields, explicit versions,
`additionalProperties: false` at structural nodes, finite numeric values,
positive physical dimensions and bounded resolutions. Validate with a declared
runtime validator; no unsafe eval, embedded Python or executable JSON strings.
Reject unsupported operations and unresolved IDs before starting Blender.

| Schema | Canonical data and checks |
| --- | --- |
| `project.schema.json` | Project/category/profile/asset_name; reference paths; scale provenance and dimensions; data-file references; materials, component configs, presentation/export/viewer policy, validation floors. Automobile category only. |
| `calibration.schema.json` | Image sizes/hashes, source selection/crop, per-view rank-two affine pixel/world maps, omitted axis/plane, cameras, landmarks, rectification and uncertainty. All four views required. |
| `cage.schema.json` | World-space finite points, typed rails/sections, symmetry plane, landmark IDs, wheel/arch guide parameters and semantic roles. Unique IDs and valid curve cardinalities. |
| `surface_graph.schema.json` | Named boundary/patch graph, approved node operation tags, curve references, support schedules, resolution, mirror/material/normal/modifier parameters. |
| `vehicle_profile.schema.json` | Expected roles and optional role cardinalities for body family; no physical coordinates. |
| `details.schema.json` (additional) | Optional large detail dataset referenced by project; same contract as inline detail config, with no duplicated authoritative values. |
| `review.schema.json` (additional) | Explicit reviewer, decision, notes, proof/output hashes and limitations; absence of review blocks release export. |

JSON Schema handles structural checks; semantic validation handles invertibility
on each view's plane, same-world wheel/ground coherence, graph cycles, reference
existence, Coons corner agreement and profile-role completeness. A schema alone
does not prove geometric correctness.

`projects/tesla/project.json` contains metadata and dimension provenance once.
It references input files, generated calibration/cage/graph and optional detail
data. All existing raw-pixel authored points are converted using the frozen
calibration during extraction; production cage/surface definitions use meters
or references to named landmarks. Raw observations remain in calibration for
traceability. No raw Tesla pixel coordinates remain in generic modules.

Proposed project structure:

```text
projects/tesla/
  project.json
  input/                         original, hash-verified images
  generated/
    calibration.json
    cage.json
    surface_graph.json
    details.json                 only if arrays merit a separate file
    silhouette_traces.json
    overlay_raw.json
  validation/                    reports, review records and real renders
  output/                        blend, GLB, viewer, optional FBX
  .cache/                        inspectable stage records/checkpoints
```

Initial profiles: sedan, fastback, fastback_suv, coupe, hatchback, wagon and suv.
Tesla references fastback_suv. Profiles use hood/front_bumper/front_fender/
front_door/rear_door/rear_quarter/roof/windshield/rear_glass/a_pillar/b_pillar/
c_pillar/rocker/trunk/hatch/rear_bumper/wheel_arch/wheel/mirror/headlight/taillight
roles with explicit optionality. Patch IDs such as L02_HOOD_SHOULDER_R and
COWL_TRANSITION belong to Tesla data, even if their semantic roles are reusable.

## Calibration API

`CalibrationTransform.pixel_to_world(view,u,v)` returns a point on the declared
reference plane. `world_to_pixel(view,x,y,z)` projects onto the same view basis;
the invisible coordinate is intentionally discarded. Roundtrip tests therefore
compare pixels or points on that plane, not arbitrary lost depth.

Store or derive an affine basis per view, including the end-view horizontal
rectification already documented by Tesla. Preserve original images and scale
assumption. Separate files for front/side/rear/top take precedence over combined
sheet crops when present. Never fit each output silhouette independently.

## Cage and surface graph

Convert K01–K35 from the audit into records; mirrored rails use a declared
symmetry axis/plane and preserve winding. Validate generated curve structure
against the delivered 53-curve baseline.

Implement only generic typed graph operations required by existing evidence:
`polyline`, `chord_hermite`, `shape_preserving_hermite`, `bezier_rail_range`,
`curve_sample`, `lerp`, `offset`, `coons`, `cubic_boundary_roll`, `arch_annulus`,
`ribbon`, `bilinear_patch`, and `boundary_stitch`. Each operation gets tests
before the Tesla data use it. Support rows and corner/normal policies are data.
Reject arbitrary expressions. Do not serialize Python lambda source into JSON.

Refinement data S24–S26 replace the superseded cowl/A-foot definitions and add
the explicit fender bridge. Preserve final geometry while eliminating the
one-off `refine_final.py` stage. Resolve boundary references by topology/parameter
identity before cleanup; raw indices must not be assumed stable after welding.
Generic surface construction must never branch on Tesla patch IDs.

Details use a bounded operation vocabulary: revolved wheel profiles, radial
spoke polygons, primitive masses, separate panels, UV-rectangle face selections,
recessed housings, curve details and surface attachments. Predicates from
build_details become declarative UV intervals. Validate source surfaces and
stable patch_u/patch_v attributes before deleting faces. Shared wheel-center
records drive cage, tires, roots and export checks.

## Standard pipeline and gates

| Stage | Dependencies and success condition |
| --- | --- |
| 01 PREFLIGHT | Load project/profile/schemas; verify inputs, capabilities and Blender executable. |
| 02 REFERENCES | Hash/decode originals, prefer separate views, prepare verified panels. |
| 03 CALIBRATION | Validate affine maps, common landmarks/ground and scale provenance; save calibrated checkpoint/proofs. |
| 04 OVERLAY EXTRACTION | HSV orange/blue/red/green segmentation and components → overlay_raw.json. Raw proposals require semantic correction; not a pass on inferred geometry. |
| 05 CAGE | Load calibrated semantic cage; resolve IDs/symmetry and save checkpoint/evidence. |
| 06 SURFACES | Resolve graph, construct independent quad/SubD surfaces and save checkpoint. |
| 07 SILHOUETTE VALIDATION | Fixed-camera masks; side≥.94, top≥.92, front≥.92, rear≥.90 for Tesla. Failure stops details. |
| 08 DETAILS | Build configured components from the passed surface checkpoint. |
| 09 GEOMETRY AUDIT | Explicit cleanup precedes read-only audit; finite/nonzero faces, roles, dimensions and exact wheel pivots checked. |
| 10 PRESENTATION | Real topology wire overlay, studio/fixed views and surface diagnostics; final silhouette rerun after details, explicit current-artifact visual review. |
| 11 EXPORT | Require final masks, geometry gate and current review; direct Blender GLB, optional supported formats. |
| 12 GLB VERIFY | Compare node structure, finite positions, triangles and bounds to evaluated Blender within existing 0.1mm tolerance. |
| 13 VIEWER | Build from verified GLB and check exact embedded digest; browser desktop/mobile controls and WebGL. |
| 14 DELIVERY | Verify all required artifacts and provenance, write project-only manifest and reports. |

Final silhouette rerun is necessary because details modify visible geometry;
the early surface pass does not authorize an altered final model indefinitely.
Human review cannot be inferred from script execution. If no valid review
exists, stage 10 is BLOCKED and dependent release stages remain BLOCKED.

Every stage records PASS, FAIL, SKIP or BLOCKED. SKIP requires a matching cache
key and verified existing outputs. FAIL is a failed executed gate; BLOCKED is
an unmet dependency/input/review/capability. Any required FAIL/BLOCKED yields a
nonzero CLI exit. The old validator's printed False cannot be treated as success.
`assert` is replaced by explicit exceptions in production gates so `python -O`
cannot disable acceptance checks.

## Cache and Blender execution

One runner discovers/configures Blender and captures command, executable/version,
source revision, stage config digest, exit code and logs. Initialize a fresh
metric scene and collections rather than requiring a preexisting Tesla blend.
Use saved stage checkpoints to allow surfaces to be skipped when only lights
change. Never open a final detailed model and add a second detail assembly.

Each stage key hashes relevant reference/config slices, implementation version
and dependency keys. Entries list outputs and their hashes; missing/corrupt
outputs invalidate the stage. Review records bind to current geometry/proof
digests. Store JSON deterministically with inspectable keys; avoid timestamps in
semantic content hashes. Configuration and output identities are separate.

- Unchanged cage/input/calibration: reuse calibration and cage checkpoints.
- Lights-only config change: reuse surfaces; rebuild details, final validation,
  presentation/review, export, GLB verification, viewer and delivery.
- Calibration change: invalidate cage and every downstream geometry stage.
- Threshold change: invalidate validation/export authorization; never reduce
  immutable Tesla floor requirements.
- Viewer label change: rebuild viewer/delivery without regenerating geometry.

## Regression and tests

Preserve delivered and audit-rerun baselines separately, including metrics,
dimensions, object structure/wheel centers, actual renders and source/output
hashes. Compare the future generic run against both. Byte-identical blend/GLB
is not required; geometric/functional equivalence is.

Required unit tests cover project/path/schema loading, all-view affine roundtrip,
invalid calibration, cage cardinality and mirrored winding, Coons planar and
curved boundaries/corner errors, graph ordering/missing IDs/cycles, thresholds
including equality/failure, gate exit behavior, phase dependencies, cache slice
invalidation and corrupted outputs. Add tests for every generic operation needed
to replace refinement/cavity logic. Run an end-to-end Tesla reconstruction in
Blender plus GLB and actual browser QA.

Minimum IoUs stay .94/.92/.92/.90. Also compare current better values, object
counts/roles, dimensions and wheel positions; a large regression cannot hide
behind floors. Define documented numeric comparison tolerances before migration
and review image differences; do not choose tolerances after observing a failure.
Geometry audit, GLB verification, viewer build, exact-GLB embedding and complete
input inventory must all pass. Archive/source geometry remains unchanged.

## Migration order and documentation

1. Finish this audit and baseline rerun; retain original source identity.
2. Add schemas/project loading and shared Blender initialization/runner.
3. Extract calibration, then cage, verifying each against the fixture.
4. Extract S01–S26 into a resolved graph; retire refinement mutation only after
   geometry equivalence is demonstrated.
5. Parameterize D01–D22; then move validation, explicit review, export and viewer.
6. Add unified CLI, deterministic phase cache and unit/integration tests.
7. Run full Tesla regression and complete all v0.1 acceptance checks; commit
   reviewable checkpoints. Do not claim v0.1 complete during the audit cycle.

Planned documents: architecture.md, project_format.md, inference_standard.md,
pipeline.md and adding_a_vehicle.md. Inference Sheet Standard v1 documents
hero 3/4 at top, FRONT|SIDE|REAR in middle, TOP at bottom; separate orthographic
inputs take priority. Color annotations: orange control points, blue visible
splines, red inferred/hidden, green datum. Image extraction proposes observations;
it does not invent a semantic model or remove the calibration gate.

Future new-vehicle workflow: create project, copy images, initialize metadata,
calibrate/generate and correct semantic data, run the standard pipeline, stop on
failed validation. New project-specific Python is forbidden. Missing generic
capabilities require evidence, reusable implementation and tests first.
