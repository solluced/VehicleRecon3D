# VehicleRecon3D v0.1 extraction audit

Audit cycle: 2026-10-15. Source: `Tesla.zip`, SHA-256
`156bd5ab0353a266e4362f282ecaac11cc7b243ae742f79eb95fd781a9aa808d`.
The archive's delivered files match the working Tesla at commit `5dad4d9`:
all 91 entries in the existing delivery manifest verified before this audit.
No reconstruction, export, viewer, or test source is changed in this cycle.
Mark II is outside this audit and remains untouched.

## Scope and counting rules

Inspected every file in `scripts/`: **20 executable scripts** (19 Python and
one Node module), plus the HTML viewer template. Also inspected the reference
metadata and traces, original handoffs, rebuild instructions, all structured
validation reports, delivery manifest, exported-model metadata, and archive
inventory. Binary models and images are covered by hashes and the baseline
rerun; they are not treated as editable framework code.

Each executable receives one primary classification below. Mixed scripts also
contain PROJECT_DATA, even though no entire current script qualifies as data.
Script totals: **GENERIC 3; GENERICIZE 15; PROJECT_DATA 0; OBSOLETE 1;
TEST/REGRESSION 1 = 20**. The template is an additional GENERICIZE asset.
There are **52 named Python function definitions**, including nested functions;
all are classified below. Lambdas and anonymous JS callbacks inherit their
owning operation's classification; geometric predicate lambdas are specifically
included in the detail migration map.

Coupling counts are **named migration units, not scalar literal counts**:
12 calibration groups; 35 cage definitions (17 rails, 14 sections, two axle
records, tire-datum template, arch-datum template); 26 surface definitions
(23 `grid()` call sites plus three corrective surface definitions); 22 detail
parameter groups. Units include repeated uses and explicit destinations below.
Polynomial coefficients, array indexing, unit vectors, and generic tolerances
are not vehicle geometry. Configurable manufacturing/presentation choices must
still leave generic algorithms, even when plausible for other automobiles.

## Script migration map

| Current script | Classification | Destination and required extraction |
| --- | --- | --- |
| `project.py` | GENERICIZE | `core/project.py`, `reference/transforms.py`, shared `blender/scene.py`, `materials.py`, `cameras.py`; remove import-time bpy/data loading, fixed root, asset path, and calibrated pixel constants. |
| `setup_reference.py` | GENERICIZE | `reference/calibration.py`, `panels.py`, `validation/render.py`; C01–C12 supply all transforms, crops, poses and datums. Explicit fresh-scene initialization must replace dependence on the saved starter. |
| `build_cage.py` | GENERICIZE | `cage/builder.py`, `curves.py`, `sections.py`; K01–K35 become cage records. Visibility restoration and diagnostic rendering remain generic. |
| `build_surfaces.py` | GENERICIZE | `surfaces/{curves,coons,patches,topology,builder}.py`; S01–S26 hold authored structure. Tire/liner logic moves to details; stage orchestration leaves math modules. |
| `build_details.py` | GENERICIZE | `details/{wheels,wheel_arches,doors,glass,mirrors,lights,bumpers,intakes,interior}.py`; D01–D22 supply dimensions, predicates, names, offsets, and styles. |
| `refine_final.py` | OBSOLETE | Retire the one-off mutation stage after its final cowl/bridge/foot data are folded into S24–S26 and reusable orientation/fitting operations. Preserve it unchanged in the source fixture until regression passes. Never silently drop its geometry. |
| `fit_lamp_returns.py` | GENERICIZE | Generic BVH surface attachment in `details/lights.py`; target, paired curve IDs and offsets from D22. |
| `presentation.py` | GENERICIZE | Shared presentation/render builder; topology-source selection, material settings, camera and studio config from project data. Keep actual mesh-derived wires. |
| `audit_geometry.py` | GENERICIZE | `surfaces/topology.py` for explicit cleanup; `validation/geometry.py` for read-only audit. Current audit welds vertices/deletes faces and saves; split these responsibilities. Selection policy and wheel bindings become configuration. |
| `inspect_surface.py` | GENERIC | `validation/render.py`: reflection-coordinate stripe render, restore material/visibility state. Minor cleanup: injected project paths and configurable render preset. |
| `render_matcap.py` | GENERIC | `validation/render.py`: Workbench matcap rendering. Minor cleanup: render preset and state restoration. |
| `render_validation.py` | GENERIC | `validation/render.py`: loop over configured calibrated views, paths and resolutions. |
| `finalize_scene.py` | GENERICIZE | Generic scene metadata writer; current EV prose, scale statement, status strings and readme text become generated project metadata. Do not treat assigned status strings as validation results. |
| `validate_silhouette.py` | GENERICIZE | `validation/silhouette.py`, `report.py`; use calibration API, project mask paths, view sizes and unchanged thresholds. A failed gate must return nonzero; current script only prints False. |
| `record_surface_review.py` | GENERICIZE | `validation/report.py`: explicit reviewer decision, notes, proof hashes and source digest. Existing fixed PASS and Tesla-specific limitations become fixture evidence, never an automatic generic acceptance. |
| `export_glb.py` | GENERICIZE | `export/glb.py`, `verify.py`: paths, collection selection and viewer group bindings from project config. Preserve in-memory curve conversion and freshness gates. |
| `verify_glb.py` | GENERICIZE | `export/verify.py`: reusable GLB parser/node comparison with injected paths and tolerance. Validate unsupported accessors explicitly. |
| `build_viewer.py` | GENERICIZE | `viewer/builder.py`: exact GLB embedding, configured labels, metadata and preset framing; preserve digest verification. |
| `test_viewer.mjs` | TEST/REGRESSION | Browser regression support under `tests/`; parameterize root, port, expected outputs and viewport policy. Retain actual desktop/mobile WebGL/control checks. |
| `finalize_delivery.py` | GENERICIZE | `core/manifest.py`, `validation/report.py`, delivery stage; move EV documentation prose and asset paths to project metadata. Do not regenerate a generic README by copying Tesla claims. |
| `viewer_template.html` (asset) | GENERICIZE | `viewer/viewer_template.html`: GLB decoder, shaders, controls and fit logic reusable; EV labels, group bindings and initial camera pose configurable. No procedural replacement geometry. |

## Complete named Python function map

Ranges refer to the unchanged scripts. Multiple names in a row share a
classification and destination. Nested names are qualified by their parent.

| Source | Function(s) | Classification | Destination |
| --- | --- | --- | --- |
| `project.py:11–14` | `sx`, `sz`, `ty`, `tx` | GENERICIZE | Replace four pixel-specific wrappers with calibrated affine transforms; constants C02–C04. |
| `project.py:15–20` | `coll`, `move`, `aim` | GENERIC | Shared Blender collection/look-at helpers. |
| `project.py:21–27` | `camera` | GENERICIZE | Shared camera helper; destination collection and pose/scale supplied. |
| `project.py:28–52` | `mat`, `emissive`, `curve`, `mesh` | GENERIC | Shared Blender construction helpers; caller supplies material, coordinates and target collection. |
| `project.py:53–59` | `save`, `render` | GENERICIZE | Project-resolved output paths and configured cameras; restore transient render state. |
| `build_cage.py:12` | `p` | GENERICIZE | Calibration adapter during extraction; serialize final cage points in meters. |
| `build_surfaces.py:14` | `p` | GENERICIZE | Calibration adapter used only while extracting legacy geometry. |
| `build_surfaces.py:27` | `cubic` | GENERIC | Cubic Bezier evaluation in `surfaces/curves.py`. |
| `build_surfaces.py:28–41` | `at_x`, `rail` | GENERICIZE | Curve evaluator with IDs/ranges supplied; no implicit `CAGE_` prefix or pixel conversion. Validate monotonic X before binary search. |
| `build_surfaces.py:43–66` | `authored`, `authored.sample`, `coons`, `coons.sample` | GENERIC | Chord-Hermite and Coons math; validate degeneracy and corner agreement. |
| `build_surfaces.py:68–95` | `finish`, `grid`, `grid.params` | GENERICIZE | Topology construction with explicit support rows, mirror axis, subdivision, thickness and material. |
| `build_surfaces.py:132–147` | `indexed`, `indexed.sample` | GENERICIZE | Shape-preserving Hermite sampler; replace the hardwired nine-point/eight-segment assumption with length-derived indexing. |
| `build_surfaces.py:154–164` | `rolled` | GENERICIZE | Reusable cubic cross-boundary roll; axle branch, coefficients and slope schedule become S08 data. |
| `build_details.py:24–37` | `flip`, `subdiv`, `mirror`, `split` | GENERIC | Topology/symmetry primitives, accepting explicit axes and IDs. |
| `build_details.py:38–47` | `box` | GENERICIZE | Primitive helper; remove global BLACK material and fixed collection defaults. |
| `build_details.py:49–79` | `cavity` | GENERICIZE | Reusable parameter-space opening cut; predicate becomes declarative UV range selection, modifiers/offsets configured. Preserve face parameter attributes before deletions. |
| `build_details.py:130–134` | `cylinder` | GENERICIZE | Wheel primitive; configurable axis, segments and collection instead of fixed wheel-local conventions. |
| `refine_final.py:20–31` | `authored`, `authored.sample` | OBSOLETE | Duplicate of surface interpolation; use the shared implementation. |
| `refine_final.py:32` | `p` | OBSOLETE | Legacy wrapper eliminated after S24–S26 extraction. |
| `refine_final.py:48–58` | `cage_x` | OBSOLETE | Duplicate Bezier/X search; replace with shared curve evaluator. |
| `validate_silhouette.py:30–43` | `polygon_mask`, `image_save`, `bbox` | GENERIC | Mask rasterization, evidence output and bounds computation with injected output directory. |
| `validate_silhouette.py:50–57` | `world`, `project` | GENERICIZE | Calibration transform plus fixed-camera projection, parameterized by view. |
| `verify_glb.py:14–18` | `mul`, `local` | GENERIC | Column-major matrix/TRS evaluation. |
| `verify_glb.py:19–35` | `points`, `walk` | GENERICIZE | GLB traversal/parser with explicit document/buffer context, validity checks and no module globals. |
| `finalize_delivery.py:5–7` | `read`, `digest`, `write` | GENERICIZE | Project-safe filesystem/manifest helpers; no fixed global root. |

## JavaScript and template functions

`test_viewer.mjs` is TEST/REGRESSION in full, including its socket listener,
polling/wait callbacks and functions `call`, `evaluate`, `frame`, `fitted`.
Its viewport sizes, fit tolerance, port and control selector names are test
policy/configuration. Its expected mesh counts and digest must always come from
the freshly verified GLB report.

In the template, `I`, `mul`, `dot`, `sub`, `cross`, `norm`, `point`, `local` are
GENERIC math. `accessor`, `shader`, `visit`, `axes`, `fit`, `matrix`, `draw`,
`requestRender`, `resize`, `activeView`, `preset`, and `qa.boundsNDC` are
GENERICIZE: bind the viewer configuration explicitly, validate supported GLB
features, retain GLB-derived geometry. The async bootstrap and every event,
array, animation, observer and pointer callback inherit GENERICIZE from this
viewer unit. Extract the pose duplicated in `state` and `preset('three')`.
Shader source is generic rendering code; shader constants are a viewer rendering
preset, not Tesla geometry. No JavaScript geometry authoring is permitted.

## Calibration constants: C01–C12

All destinations below are within the future `projects/tesla/` directory.
`project.json` is abbreviated P; `generated/calibration.json` is C. Generated
calibration owns transforms/landmarks; P references it without copying values.

| ID | Existing source and complete constant group | Destination |
| --- | --- | --- |
| C01 | `refs/reference_data.json:scale`: length 4.8, width 1.8823529411764706, height 1.5257844474761255, wheelbase 3.077762619372442, radius 0.40600272851296043, tracks 1.61/1.64, scale provenance | P dimensions/scale provenance; derived values checked against C, not independently reauthored. |
| C02 | `project.py:8–12`: 733, 761.5, 741; side mappings repeated through `p()` and silhouette `world()` | C `views.side.pixel_to_world`; matrix coefficients derived once from landmarks. |
| C03 | `project.py:13–14`: 932, 280, 760, 714; top mappings repeated in setup and mask validation | C `views.top.pixel_to_world`. |
| C04 | End-view width normalization, centerline, front sign in `setup_reference.py:32–36`, `validate_silhouette.py:53–54` | C front/rear affine maps with explicit anisotropic correction. |
| C05 | `refs/reference_data.json:source_size/views`: all four crop and body bbox arrays; fixed 1152×1536 reshape in setup:24 | C image/panel records; image dimensions verified against actual decoded inputs. |
| C06 | Side axle pixels (520,679)/(990,681), radii 64/60 in reference data | C landmark observations/provenance; downstream resolved wheel centers referenced by cage. |
| C07 | Front/rear centerlines, ground/roof rows and track center pixels in reference data | C front/rear landmarks; preserve uncertainty. |
| C08 | `reference_data.json:uncertainty`, approximately 3px error, 6.45% tire mismatch, 0.8763 front correction and reconciliation policy; dimensional notes | C uncertainty/rectification and P provenance notes. |
| C09 | `setup_reference.py:18–22`: five initial camera poses, targets and ortho scales | C calibrated cameras; final 3/4 pose is presentation override in P. |
| C10 | `setup_reference.py:29–36`: side Y=1.35, top Z=-.08, end X=±2.65, vertex orientation/UV scheme | C plane placement; orientation/UV algorithm generic. |
| C11 | `setup_reference.py:59–73`: u=395/520/990/1128, ground/radius/height lines, bounds 385/1140/±1.05, datum offsets and radii | C datum records referencing landmarks; visual style in P render preset. |
| C12 | `setup_reference.py:61–81`: per-view proof sizes, composite 2000×1120 positions/sizes; validation/render/cage fixed render lists | P render presets and alignment-proof layout. |

## Cage definitions: K01–K35

K01–K17 are each of the **17 entries** of `build_cage.py:24–42` RAILS,
in source order: L00_CENTERLINE, L01_HOOD_CENTER, L02_HOOD_SHOULDER,
L03_FRONT_FENDER_CROWN, L04_UPPER_ARCH_TRANSITION, L05_BELT,
L06_SHOULDER_CHARACTER, L07_DOOR_LOWER_CHARACTER, L08_ROCKER_UPPER,
L09_ROCKER_LOWER, L10_WINDOW_SILL, L11_ROOF_EDGE, L12_ROOF_CENTER,
L13_REAR_QUARTER_SHOULDER, L14_HATCH_TRANSITION, L15_LOWER_BUMPER,
L15_REAR_LOWER_BUMPER. Every point triple and semantic ID moves to
`generated/cage.json:rails`, calibrated into world meters. Symmetry is explicit
data; IDs are resolved from records, never hardwired in a generic builder.

K18–K31 are **14 independent sections**, T00 through T13 in
`build_cage.py:51–66`. All section X positions and half-section point pairs move
to `generated/cage.json:sections`, using world-space coordinates and symmetry.

K32/K33 are front/rear axle records in `build_cage.py:71`: u=520/990,
tracks 1.61/1.64, side signs. K34 is the tire-datum template in :75–76:
radius/height .406 and 12 circular samples. K35 is the arch-datum template in
:77–78: .465 radius, .89/.051 width shaping, .406 height and angle schedule
[-22,0,35,70,90,110,145,180,202]. These become `cage.json:landmarks/wheel_guides`
referencing resolved dimension IDs, with generic circular/arch sampling.
Do not maintain competing wheel-center/radius copies in detail data.
Cage materials, bevels .003/.0022/.0025/.004 and render sizes move to P styles.
The source expands these records into **53 actual curves**.

## Surface definitions: S01–S26

Each grid call site is listed, including those expanded by loops. All point
arrays, curve IDs/ranges, resolutions, support rows, normals, mirroring,
materials and thicknesses move to `generated/surface_graph.json`; independent
reusable evaluators stay in `vehiclerecon/surfaces/`. Math callbacks become
typed graph nodes, not Python expressions stored in JSON.

| ID | Source | Definition/data to preserve |
| --- | --- | --- |
| S01 | `build_surfaces.py:98–102` | HOOD: two cage ranges, authored front/back transverse controls. |
| S02 | :103–105 | COWL_TRANSITION with .012 crown offset; final replacement is S24. |
| S03 | :106 | Initial PILLAR_A_FOOT corners/resolution; replaced by S26. |
| S04 | :109–112 | NOSE_HOOD_BRIDGE top/lower/crown control arrays. |
| S05 | :113–114 | NOSE_CHEEK cage samples and authored corner. |
| S06 | :115–117 | BUMPER_FRONT Coons boundaries and side/center bulge points. |
| S07 | :118–119 | LIP_FRONT lower profile, material, normal. |
| S08 | :123–165 | FENDER_FRONT/REAR: both outer point lists and final overrides, inner angular schedule, nine-point indexed C1 interpolation, cubic roll coefficients, rear slope array. Record original overridden arrays as provenance; active values alone drive generation. |
| S09 | :166 | ARCH_RETURN_FRONT/REAR inset .028, normal and resolution. |
| S10 | :175–182 | Both door lower/upper/left/right point arrays and panel-gap intent. |
| S11 | :185–187 | BELTLINE_LEDGE body belt array and window-sill curve range. |
| S12 | :191–197 | Windshield/roof/rear-glass intervals, center/edge rails, rear override and .012 transverse crown. |
| S13 | :200–205 | Both side-glass lower/upper point arrays. |
| S14 | :206–207 | Upper frame boundaries derived from glass and roof-edge rail. |
| S15 | :206–208 | Lower frame boundaries derived from glass and sill rail. |
| S16 | :209–211 | Front/back frame patches, sample endpoints and material selection bindings. |
| S17 | :215–216 | ROOF_RAIL cage range and transverse ribbon offsets. |
| S18 | :217 | Initial PILLAR_B corners; detailed replacement in D10. |
| S19 | :220 | PILLAR_C_QUARTER authored lower/upper boundaries. |
| S20 | :221–223 | REAR_HATCH_TOP front and lip arrays. |
| S21 | :224–225 | REAR_HATCH lower boundary and lip reference. |
| S22 | :226–229 | BUMPER_REAR low, top and bowed side/center arrays. |
| S23 | :233–234 | ROCKER lower/upper arrays. |
| S24 | `refine_final.py:33–43` | Final cowl rebuild boundaries and orientation. Fold into S02 active data. |
| S25 | :46–70 | Fender-cowl boundary bridge: selected parameter interval .6249–.7501, cage range 580.3–623, interpolation rows .33/.66/.98/1. Generic boundary-stitch operation; no final dependency on raw vertex indices after cleanup. |
| S26 | :71–81 | Final A-foot four corners, support schedule, SubD and wall thickness. Fold into S03 active data. |

`finish()` thickness .0025, mirror merge .0001, grid support .012/.988,
default resolution/subdivision, normal policies and all material colors in
`build_surfaces.py:15–19` are project surface/material settings, not concealed
geometry defaults. The wheelhouse backing fan :168–171 (radius .464, depth .65,
height .25/.406, angle span/sample count) becomes a configured wheel-arch detail
operation. Tire/profile data :236–252 are D13–D14. Studio lights :260–264 move
to the project presentation preset, including positions, power, size and target.

## Detail constants: D01–D22

Destination is `project.json:details` with large authored arrays optionally in
referenced `generated/details.json`. Cross-references point to cage landmarks,
surface IDs and material IDs. This optional extra file is schema-defined, not
project-specific Python. Repeated values are resolved once by ID.

| ID | Existing source | Parameter group and future component |
| --- | --- | --- |
| D01 | `build_details.py:15–22`; material setup in surface/presentation scripts | All named colors, roughness, metallic, transmission/emission values → P materials. |
| D02 | :81–84 | Headlight source binding, UV predicate (.02/.98, .04/.65), recess offset, left/right names, LED edge offset/radius → lights. |
| D03 | :86 | Central intake UV limits and recess offset → intakes. |
| D04 | :87–88 | Side intake UV limits, offsets and split names → intakes. |
| D05 | :89–90 | Three grille heights and five-point slat array/radius → intakes. |
| D06 | :92–93 | Rear-light UV region, offset and names → lights. |
| D07 | :94–96 | Diffuser UV region, recess, five fin Y values, position/size/bevel → bumpers. |
| D08 | :100–109 | Door source/name bindings, .003 seam, .008 backing inset → doors. |
| D09 | :110–113 | Side-glass split IDs and superseded frame IDs → glass. |
| D10 | :114–117 | Replacement B-pillar four corners, mirror, thickness .005, bevel .002/segments → glass/pillar operation. |
| D11 | :118–120 | Handle axle-independent positions u=782/932, Y/Z, box dimensions/bevel → doors. |
| D12 | :124–127 | Mirror stem points, housing/glass positions, sizes and bevels → mirrors. |
| D13 | `build_surfaces.py:236–242` | Eight-point tire cross-section and 64 segments → wheels. |
| D14 | :244–252 | Four wheel mounting records, tire height and blockout disc radius/depth; resolve shared K32/K33 references → wheels. |
| D15 | `build_details.py:135–147` | Wheel root hierarchy, brake plane, six-point rim profile and segmentation → wheels. |
| D16 | :148–157 | Ten-spoke count, four radial/angular polygon controls, side depth, Solidify/bevel/normal modifiers → wheels. |
| D17 | :158–163 | Hub/cap/lug radii/depth/locations, five-lug count and bolt-circle radius → wheels. |
| D18 | :166–171 | Seat base/back/headrest pairs, back angle and rear bench/backrest masses → interior. |
| D19 | :172–174 | Dashboard, console, display transforms/dimensions/bevels → interior. |
| D20 | :175–177 | Steering torus dimensions/segments/pose and floor box → interior. |
| D21 | `refine_final.py:10–18` | Spoke orientation selection and brake depth correction → generic normal policy plus final D15/D16 parameter values; retire corrective loop. |
| D22 | `refine_final.py:84–88`; `fit_lamp_returns.py:8–17` | Four-point rear-return curves, offset/lens radii, hatch binding, paired curve names and .002/.010 evaluated-surface attachment distances → lights. |

`cavity()` contains additional modifiers/crease .72, housing thickness .004,
edge offset .003 and smoothing settings (:49–79). Those belong to the component
settings, alongside D02–D07, rather than numeric defaults chosen for this Tesla.
Primitive bevel/segments and wheel cylinder segments also become explicit style
parameters. Vertex deletion and edge parameter bookkeeping remain algorithms.

## Remaining coupling and non-code assets

| Current material | Migration |
| --- | --- |
| `refs/reference_data.json` and `docs/reference_dimensions.md` | Split measured/assumed dimensional metadata into P and affine calibration into C; retain provenance/uncertainty text. |
| `refs/silhouette_traces.json` | `projects/tesla/generated/silhouette_traces.json`; manual fixture observations, never a generic car silhouette. |
| Five original `refs/reference_*.png`, `refs/manifest.json` | `projects/tesla/input/` plus hash metadata; derived crops become generated/cache artifacts. |
| `presentation.py:11–31` | Material overrides, 24 wire source IDs, wrap offset .0008, wire .0018, studio ground and final 3/4 pose → P presentation. Generic edge overlay uses resolved source IDs. |
| All collection/object naming filters in cleanup, audit/export/viewer | P bindings/export selection or semantic profile roles; no Tesla patch-name lists in algorithms. Canonical automobile roles may remain vocabulary. |
| Hardcoded `.blend`, GLB, report and reference filenames across scripts | Project-resolved paths; `asset_name` from P. |
| `validate_silhouette.py:46` | Thresholds .94/.92/.92/.90 and render sizes → P validation; retain floors in immutable regression fixture. |
| `verify_glb.py:38–43` | .0001m comparison tolerance → validation policy; world-coordinate conversion is a documented export convention. |
| `record_surface_review.py:17–21` | Reviewed zones, source limitations and 4.8m assumption → explicit project review record, never fixed generic PASS. |
| `finalize_scene.py:9–23`, `finalize_delivery.py:28–115` | EV/53-curve/4.8m/envelope/topology prose → metadata-derived reports or Tesla fixture notes, never global templates with Tesla values. |
| `finalize_delivery.py:19–26,121–131` | Required files/manifest scope → delivery config; discovery must exclude runtime caches and unrelated projects. |
| `viewer_template.html` | Title/eyebrow/accessibility text and initial state/preset pose → P viewer metadata. Shader/fit interaction logic reusable. |
| Saved Blender scene | Regression artifact only. It supplies existing collections, metric units, world, scene and READ_ME_FIRST text that current setup assumes; fresh-scene construction is a required extraction capability. |
| Existing validation and exports | Immutable delivered baseline; freshly rerun results recorded separately. Hashes are provenance, not byte-identity acceptance for future blends/GLBs. |
| `__pycache__`, old diagnostic `.log`, ignored preview/browser state | OBSOLETE runtime artifacts; omit from distribution and fixture identity. |

## Baseline and current architectural gaps

Baseline evidence is stored in `tests/fixtures/tesla/baseline/` with separate
`delivered/` and `rerun/` results. `output_manifest.json` records original source
hashes; `comparison.json` records rerun status and geometric differences.
The rerun uses unchanged scripts extracted from Tesla.zip in an isolated working
copy. It never rebuilds over the delivered root asset.

Current gates: details requires the saved silhouette flag and the undetailed
DOOR_F object; export checks mask/review state and source blend digest; GLB and
viewer verification check geometry/digests. Missing framework capabilities:
validated project schemas, unit-testable pure math, declarative patch graph,
fresh-scene initialization, consolidated Blender runner, explicit human review
input, read-only audit, failure exit propagation and phase caching.
No generic package or v0.1 acceptance is claimed by this audit.

### Completed legacy rerun

| Check | Delivered | Isolated rerun |
| --- | --- | --- |
| SIDE IoU (minimum .94) | .957230 | .957230 |
| TOP IoU (minimum .92) | .936083 | .936083 |
| FRONT IoU (minimum .92) | .931202 | .931202 |
| REAR IoU (minimum .90) | .944724 | .944724 |
| Geometry audit | PASS | PASS |
| Exported GLB verification | PASS | PASS |
| Desktop/mobile browser controls | PASS | PASS |
| GLB mesh nodes / triangles | 191 / 245,952 | 191 / 245,952 |
| Scene object count | 262 | 262 |
| Surface control faces / quads | 3,693 / 3,686 | 3,693 / 3,686 |
| Wheelbase from wheel roots | 3.077762722969055 m | 3.077762722969055 m |

All vehicle control-mesh and curve hashes, object IDs, transforms, cameras,
collections, body envelope, wheel centers and exported source-geometry records
match exactly. One scene-state difference is retained explicitly: the delivered
STUDIO_GROUND has hide_render=true, while the rebuilt presentation ground has
hide_render=false. Ground is excluded from masks and exports; its geometry also
matches. The cleanup log additionally reports a frame corner cleanup on the
fresh rebuild; final control geometry matches. These differences are evidence,
not reasons to edit Tesla during the audit.

The saved blend and GLB byte hashes differ, as permitted; both identities and
every original/rerun output hash are recorded in the fixture. The rebuilt HTML
was independently decoded and its embedded bytes match the rebuilt GLB exactly.
The first sandboxed browser attempt exited before its CDP session initialized;
the same unchanged browser test passed with approved execution outside the
sandbox. The isolated browser was closed after QA.

Baseline source: Blender 5.2.2 LTS; Node 24.18.0; installed Microsoft Edge.
Actual rebuilt studio, reflection, matcap and four orthographic renders were
opened before running the legacy review recorder. This is a baseline visual
review preserving the existing output, not a claim of improved Tesla quality.

The separate Mark II folder was already untracked before this audit. It is
outside the migration and must not be incorporated into the Tesla fixture or
silently included by a delivery manifest.
