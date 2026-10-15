# VehicleRecon3D architecture

Version 0.1 separates automotive algorithms from authored vehicle data.
`vehiclerecon/` contains reusable Python. `projects/<id>/` contains metadata,
reference images and all geometry/configuration. `profiles/` defines semantic
automobile families without dimensions. `schemas/` defines Draft 2020-12
contracts. `tests/fixtures/tesla/baseline/` is frozen acceptance evidence;
`tests/fixtures/tesla/legacy_source/` retains the original project unchanged.
The extraction audit's historical `scripts/...` paths now refer to that archive.

| Boundary | Responsibility |
| --- | --- |
| core | Project/path/schema loading, stage ordering, content cache, manifests and explicit errors. |
| reference | Affine calibration, panel selection, source identities and raw color proposals. |
| cage | World-space rail/section records, symmetry, landmarks and shared wheel/arch guides. |
| surfaces | Pure Hermite/Bezier/Coons mathematics, bounded graph resolution, sampling and topology policy. |
| details | Parameterized wheels, arches, panels, glass, mirrors, apertures and interior primitives. |
| blender | The only bpy/bmesh/mathutils adapters: fresh scenes, geometry construction, render/audit/export workers. |
| validation | Fixed-mask metrics, explicit review, functional baseline comparisons and render-container normalization. |
| export | GLB integrity and evaluated-source verification. FBX explicitly reports unavailable. |
| viewer | Metadata/template packaging and isolated desktop/mobile WebGL QA. Geometry comes exclusively from GLB. |

Pure modules import under ordinary Python; only Blender adapters import Blender
APIs. A single runner discovers Blender, always passes `--python-exit-code 1`,
and captures command, version, project/stage, return code and stdout/stderr.
Every rebuild begins from factory-empty metric scene data, never a saved Tesla.

Surface graphs have a bounded operation vocabulary; no eval/exec or source-code
predicates are accepted. The extracted graph retains independent authored
boundaries, real arch annuli and the final cowl/bridge/A-foot geometry. It does
not reconstruct a whole body by silhouette lofting or serialize a finished
vehicle mesh as a substitute for reconstruction.

Topology cleanup is an explicit operation. The following audit is read-only and
checks that geometry hashes remain unchanged during inspection. Semantic roles,
physical envelope, finite/nonzero faces and wheel-axis roots are validated.
Rendering, silhouette acceptance and visual review remain separate gates.

Explicit review records bind reviewer/decision/notes/limitations to evaluated
geometry, model inputs and actual proof bytes. The pipeline never writes a
review decision itself. PNG render text metadata (date/timing/path) is removed
without changing IDAT or color-profile chunks, so review hashes reflect stable
artifacts. Execution provenance is retained in JSON/text sidecars.

Stage cache records include implementation-content identity, scoped inputs,
dependency result identities and verified output hashes. Dependency identities
include output bytes, so replacement Blender checkpoints invalidate dependent
mask/source bindings. Presentation assets have a separate cache entry so an
explicit review can resume acceptance without overwriting reviewed proofs.

Legacy physical bounds and triangle counts are compared strictly. Diagnostic
topology overlays are reported separately: cowl welding removes 32 redundant
wire triangles and changes that overlay's bounds by 0.160336 mm. Physical parts
retain baseline bounds/counts. Every current GLB node, including overlays, is
still compared to evaluated Blender within 0.1 mm. This distinction is recorded
in the regression evidence; minimum silhouette floors are unchanged.
