# PRODUCTION ADDENDUM — REFERENCES ARE BUNDLED

**This archive is self-contained. Do not stop with a "reference images missing" status.**

Before any geometry work, verify these exact files exist and are readable:

- `refs/reference_multiview.png` — **PRIMARY GEOMETRIC SOURCE OF TRUTH**. Use for FRONT / SIDE / REAR / TOP proportions, wheelbase, silhouette, greenhouse, overhangs and wheel placement.
- `refs/reference_surface_target.png` — **QUALITY / SURFACE / TOPOLOGY TARGET**. Match the clean semi-transparent automotive SubD/NURBS-like surface and coherent blue edge flow. Do not treat this image as an independent dimensional source when it conflicts with the multiview.
- `refs/reference_workflow.png` — **PROCESS + QUALITY TARGET**. The lower-row block **#2 "3D SURFACE MODEL"** is the required presentation/quality benchmark. The control-cage stages illustrate intended method, not permission to invent geometry.
- `refs/reference_dense_control_points.png` — secondary study reference showing desired dense semantic tracing. Use it to understand feature coverage, not as authoritative geometry.
- `refs/reference_control_cage_overlay.png` — secondary cage/curve study. Use it only to help identify semantic feature lines.

## Reference priority on conflict

1. `reference_multiview.png` — geometry/proportions
2. cross-view consistency between FRONT/SIDE/REAR/TOP
3. `reference_surface_target.png` — surface quality/topology/presentation
4. `reference_workflow.png` — workflow intent and block #2 quality benchmark
5. secondary annotated references — guidance only

## Hard anti-shakal constraints

- Do **not** generate a generic Tesla-like car from memory.
- Do **not** use `SIDE silhouette + TOP width + FRONT section -> automatic loft` as the final-body method.
- Do **not** create a capsule/blob and decorate it with blue wire lines.
- Do **not** claim validation passes unless actual renders are compared to the bundled multiview.
- Do **not** generate GLB/HTML before Blender geometry passes FRONT/SIDE/TOP/REAR validation.
- HTML must display the exact Blender-exported GLB, never a second procedural model.
- If a surface feature is ambiguous, document the ambiguity and infer it from adjacent views; do not silently invent a generic automotive shape.

## Mandatory first action

Open the bundled images, record their pixel dimensions and establish calibrated reference planes in Blender. Update `docs/reference_dimensions.md`, render the alignment proof, and then begin the semantic 3D curve cage.

---

PROJECT HANDOFF — TESLA-LIKE EV SURFACE MODEL
TARGET: PRODUCTION-QUALITY BLENDER 3D RECONSTRUCTION
MODE: REFERENCE-DRIVEN / SURFACE-MODELING / NO GENERIC BLOB LOFTING

====================================================================
0. PRIMARY GOAL
====================================================================

Reconstruct the Tesla-like vehicle shown in the supplied multi-view
reference sheet as a real Blender 3D model.

The visual target is NOT a generic Tesla-like car.

The target quality is specifically the clean "3D SURFACE MODEL"
shown in the lower row, block #2 of the supplied reconstruction
workflow image:

- accurate overall proportions;
- correct roof / hood / greenhouse / rear silhouette;
- clean automotive surface flow;
- coherent SubD topology;
- recognizable front and rear geometry;
- correct wheel placement and wheel arches;
- real doors/windows/pillars/panel boundaries;
- professional blue-wireframe-over-surface presentation;
- model must survive FRONT / SIDE / TOP / 3/4 validation.

DO NOT produce:
- a generic lofted shell;
- a stretched ellipsoid;
- a procedural blob;
- a car generated only from outer silhouettes;
- a single surface with wireframe drawn over it;
- a mesh that only looks acceptable from one camera angle.

This is a reference-constrained automotive modeling task.

====================================================================
1. SOURCE OF TRUTH
====================================================================

Use the supplied multi-view inference sheet containing:

- FRONT VIEW
- SIDE VIEW
- REAR VIEW
- TOP VIEW
- PERSPECTIVE VIEW

Also use the supplied clean blue-wireframe render as the QUALITY TARGET.

IMPORTANT:

The clean blue-wireframe render is not authoritative for exact dimensions.
It is the quality / topology / presentation target.

The multi-view sheet is authoritative for:

- proportions;
- silhouette;
- wheelbase;
- roof profile;
- body width;
- hood length;
- rear taper;
- greenhouse placement;
- wheel positions.

Create a folder:

/refs/

Place references there using names:

refs/reference_multiview.png
refs/reference_surface_target.png
refs/reference_workflow.png

If exact filenames differ, detect them and document actual filenames.

====================================================================
2. ABSOLUTE MODELING RULE
====================================================================

DO NOT create the final body by simply:

SIDE silhouette
+
TOP width profile
+
FRONT cross-section
+
automatic loft

That exact method previously produced unacceptable geometry.

Instead use FEATURE-BASED SURFACE RECONSTRUCTION.

The body must be reconstructed from multiple independent feature curves
and sectional constraints.

Required feature families:

LONGITUDINAL:

L00 vehicle centerline
L01 hood center crown
L02 hood shoulder left/right
L03 front fender crown left/right
L04 upper wheel-arch transition
L05 beltline left/right
L06 shoulder/body character line
L07 door lower character line
L08 rocker upper edge
L09 rocker lower edge
L10 window sill
L11 roof edge
L12 roof center
L13 rear quarter shoulder
L14 rear hatch/trunk transition
L15 lower bumper line

TRANSVERSE:

T00 front bumper section
T01 front lamp section
T02 hood-front section
T03 front wheel center
T04 rear of front wheel
T05 A-pillar
T06 front seat / B-pillar zone
T07 B-pillar
T08 rear door zone
T09 C-pillar
T10 rear wheel center
T11 rear quarter
T12 rear lamp section
T13 rear bumper

These curves / sections must control the final surface.

====================================================================
3. SCENE SETUP
====================================================================

Use Blender.

Preferred:
Blender 4.x current stable available on machine.

Units:
Metric.

Vehicle coordinate convention:

X = vehicle longitudinal axis
    front = negative X
    rear = positive X

Y = vehicle lateral axis
    left/right

Z = up

Origin:
vehicle centerline,
ground plane approximately Z=0.

Nominal envelope for initial calibration only:

length  ≈ 4.8 m
width   ≈ 1.9–2.0 m
height  ≈ 1.5–1.6 m

Do NOT force these numbers if reference proportions indicate otherwise.

Determine the normalized reference ratios first.

====================================================================
4. REFERENCE CALIBRATION — MANDATORY
====================================================================

Before modeling any body surface:

create orthographic cameras:

CAM_FRONT
CAM_REAR
CAM_SIDE
CAM_TOP
CAM_3Q

Create image reference planes:

REF_FRONT
REF_SIDE
REF_REAR
REF_TOP

Align them so:

- wheel centers match between FRONT/SIDE/TOP;
- vehicle centerline matches;
- overall length matches;
- overall width matches;
- roof height matches;
- ground plane matches.

Do not eyeball each view independently.

All orthographic references must live in ONE coherent coordinate system.

Document:

wheelbase
front overhang
rear overhang
overall length
overall width
overall height
wheel radius
front track
rear track

in:

docs/reference_dimensions.md

Use ratios if absolute dimensions cannot be inferred reliably.

====================================================================
5. FIRST MILESTONE — 3D CURVE CAGE
====================================================================

DO NOT start by creating a dense body mesh.

First build a sparse but accurate 3D cage.

Collection:

00_REFERENCE
01_CURVE_CAGE
02_BLOCKOUT
03_BODY
04_PANELS
05_GLASS
06_LIGHTS
07_WHEELS
08_INTERIOR
09_PRESENTATION

Build the feature curves listed in section 2.

Curve names must be explicit, e.g.:

CAGE_L_HOOD_CENTER
CAGE_L_HOOD_SHOULDER_L
CAGE_L_HOOD_SHOULDER_R

CAGE_L_BELT_L
CAGE_L_BELT_R

CAGE_L_ROOF_CENTER
CAGE_L_ROOF_EDGE_L
CAGE_L_ROOF_EDGE_R

CAGE_T_FRONT_WHEEL
CAGE_T_A_PILLAR
CAGE_T_B_PILLAR
CAGE_T_REAR_WHEEL

etc.

Use mirror symmetry where appropriate.

The cage MUST reproduce:

SIDE silhouette
TOP silhouette
FRONT silhouette

before any finished body surface is created.

====================================================================
6. CURVE DENSITY RULE
====================================================================

Do not use dozens of meaningless evenly spaced control points.

Use control points at geometric events:

- curvature inflection;
- panel transition;
- wheel-arch tangent;
- pillar transition;
- hood/fender break;
- roof maximum;
- rear taper transition;
- bumper corner;
- rocker transition.

Then use Bezier handles / spline interpolation.

Required principle:

MINIMUM control points
+
MAXIMUM geometric meaning.

A smooth car body is not created by point spam.

====================================================================
7. BODY CONSTRUCTION
====================================================================

After cage validation passes:

create:

BODY_MASTER

Preferred workflow:

- quad patch modeling;
- Subdivision Surface;
- shrink/curve-controlled placement where useful;
- mirror modifier;
- explicit supporting loops only where shape requires them.

Alternative:
NURBS patches may be used if they produce superior curvature continuity,
but final deliverable must include a usable polygon/SubD representation.

DO NOT build the entire car as one huge arbitrary loft.

Break conceptual surface zones into:

01 hood
02 front bumper
03 front fender
04 front door
05 rear door
06 rear quarter
07 roof
08 A/B/C pillars
09 rocker
10 rear hatch/trunk region
11 rear bumper

The final exterior may later be merged where appropriate.

====================================================================
8. TOPOLOGY REQUIREMENTS
====================================================================

Main body topology:

- predominantly quads;
- no random triangulation on visible Class-A-like surfaces;
- edge flow follows curvature;
- edge flow bends around wheel arches;
- clean loops around windows;
- clean loops around headlights;
- clean loops around door openings;
- no pinching on hood;
- no pinching on roof;
- no starburst topology in broad reflective surfaces.

Poles:
allowed only in low-curvature / visually safe regions.

Do not place high-valence poles:

- on hood crown;
- roof center;
- door center;
- primary shoulder line;
- fender crown.

Use subdivision level:

Viewport 1–2
Render 2–3

as appropriate.

====================================================================
9. WHEEL ARCHES
====================================================================

Wheel arches are CRITICAL.

They must not be painted curves.

They must exist in geometry.

Front/rear wheel centers come from SIDE reference.

Arch shape must be checked against:

SIDE
FRONT/REAR
TOP

Build actual arch topology with:

- correct radius;
- correct lip thickness;
- correct flare;
- tangent transition into fender;
- correct front/rear opening geometry.

The wheel must visually sit inside the arch correctly.

====================================================================
10. GREENHOUSE / GLASS
====================================================================

The previous failed versions treated the greenhouse as part of a generic blob.

Do not repeat this.

Create separate:

GLASS_WINDSHIELD
GLASS_ROOF
GLASS_FRONT_LEFT
GLASS_FRONT_RIGHT
GLASS_REAR_LEFT
GLASS_REAR_RIGHT
GLASS_REAR

Create actual:

A-pillar
B-pillar
C-pillar

geometry.

Match:

- windshield angle;
- roof apex;
- side glass lower edge;
- rear glass taper;
- D/C pillar transition;
- panoramic roof proportions.

====================================================================
11. DOORS AND PANEL LINES
====================================================================

Create real panel structure:

DOOR_FL
DOOR_FR
DOOR_RL
DOOR_RR
HOOD
REAR_HATCH

Panel gaps must exist as geometry or controlled inset seams.

Do not paint them onto the material.

Target panel-gap appearance:
approximately realistic automotive scale.

Flush door handles:
model them as separate simple geometry.

====================================================================
12. FRONT END
====================================================================

The front must include real recognizable forms:

- hood leading edge;
- headlight cavities;
- left/right headlight bodies;
- front bumper volume;
- lower central intake;
- side lower inlets;
- lower lip;
- bumper/fender transitions.

Objects:

LIGHT_HEAD_L
LIGHT_HEAD_R
BUMPER_FRONT
INTAKE_CENTER
INTAKE_SIDE_L
INTAKE_SIDE_R

The nose must not remain a blank rounded block.

====================================================================
13. REAR END
====================================================================

Create:

rear hatch/trunk surface
rear lamp region
rear bumper
lower diffuser/black lower section

Objects:

LIGHT_TAIL_L
LIGHT_TAIL_R
BUMPER_REAR
DIFFUSER_REAR

Match REAR view.

====================================================================
14. WHEELS
====================================================================

Model wheels sufficiently close to the reference.

Do not use plain cylinders.

Need:

- tire;
- rim;
- center hub;
- approximately correct spoke count/style;
- believable tire sidewall.

Objects:

WHEEL_FL
WHEEL_FR
WHEEL_RL
WHEEL_RR

Use instances where possible.

====================================================================
15. INTERIOR
====================================================================

Interior is SECONDARY but visible through glass.

Minimum:

- front seats;
- rear seats;
- dashboard mass;
- steering wheel;
- center console.

Do NOT spend excessive time on detailed interior until exterior passes validation.

====================================================================
16. MATERIALS
====================================================================

Create simple presentation materials:

MAT_BODY_SURFACE
light gray / pearl white
roughness ~0.25–0.35

MAT_GLASS
transparent dark gray

MAT_WIREFRAME
blue

MAT_TIRE
dark rubber

MAT_RIM
dark metallic gray

MAT_LIGHT_FRONT
MAT_LIGHT_REAR

The target viewport/presentation should resemble:

white/semi-transparent surface
+
fine blue wireframe

as shown in target block #2.

====================================================================
17. WIRE OVERLAY
====================================================================

The blue wireframe must represent REAL topology / edge flow.

Do not generate fake decorative grid lines unrelated to geometry.

Preferred options:

A:
duplicate body
+
Wireframe Modifier

or

B:
Freestyle / geometry nodes using actual mesh edges.

Wire should be:

thin
blue
clean
consistent
not visually overpowering.

====================================================================
18. VALIDATION LOOP — MANDATORY
====================================================================

After EVERY major body milestone produce:

validation/front.png
validation/side.png
validation/rear.png
validation/top.png
validation/perspective.png

Orthographic renders must use the calibrated cameras.

Then compare against reference.

Do NOT continue to detail work if the basic silhouette is wrong.

Validation order:

1. SIDE
2. TOP
3. FRONT
4. REAR
5. 3/4

SIDE/TOP/FRONT must pass before details.

====================================================================
19. SILHOUETTE ERROR CHECK
====================================================================

Where possible, automate silhouette comparison.

Create:

scripts/validate_silhouette.py

Workflow:

render black model silhouette on white background
compare to normalized reference mask
calculate:

IoU
pixel mismatch %
bounding-box difference

Save reports:

validation/report.json

Suggested acceptance:

SIDE IoU >= 0.94
TOP IoU  >= 0.92
FRONT IoU >= 0.92
REAR IoU >= 0.90

These are guidance thresholds.

Do not game the metric by merely matching the outer shell while destroying
surface quality.

====================================================================
20. CURVATURE / SURFACE QUALITY CHECK
====================================================================

Inspect:

- zebra stripes;
- matcap;
- reflection lines;
- subdivision preview;
- curvature continuity.

Look specifically for:

- hood waviness;
- roof waviness;
- fender pinching;
- wheel-arch pinching;
- C-pillar lumpiness;
- rear-quarter dents;
- door surface discontinuity.

Fix these before final export.

====================================================================
21. REQUIRED BLENDER PRESENTATION
====================================================================

Create scene:

SCENE_PRESENTATION

Camera angle:
front-left 3/4,
similar to target surface-model render.

Lighting:
large soft studio area lights.

World:
very light neutral gray.

Ground:
subtle shadow plane.

Render target should visually resemble the supplied clean blue-wireframe render.

The car should occupy approximately 75–85% of image width.

No tiny car floating in a huge empty frame.

====================================================================
22. HTML VIEWER
====================================================================

ONLY AFTER the Blender model passes validation:

export GLB:

exports/tesla_surface_model.glb

Then create:

exports/viewer.html

HTML viewer must display the ACTUAL GLB model.

Do not recreate geometry separately in JavaScript.

Preferred:
Three.js or model-viewer if a local self-contained build is practical.

Viewer requirements:

- orbit rotation;
- pinch zoom;
- mouse wheel zoom;
- FRONT;
- SIDE;
- REAR;
- TOP;
- 3/4;
- FIT MODEL;
- toggle body;
- toggle wireframe;
- toggle glass;
- toggle wheels;
- reset camera.

Initial view:
same as Blender presentation camera.

The car must automatically fit the viewport correctly on desktop AND mobile.

====================================================================
23. DELIVERABLES
====================================================================

Required:

tesla_surface_model.blend

exports/
    tesla_surface_model.glb
    viewer.html

validation/
    front.png
    side.png
    rear.png
    top.png
    perspective.png
    report.json

docs/
    reference_dimensions.md
    modeling_notes.md
    validation_summary.md

scripts/
    setup_reference.py
    validate_silhouette.py
    export_glb.py
    render_validation.py

Optional:

exports/tesla_surface_model.fbx
exports/tesla_surface_model.obj

====================================================================
24. BLENDER PYTHON
====================================================================

Use bpy wherever automation is useful:

- reference setup;
- collections;
- camera setup;
- materials;
- validation renders;
- export;
- object naming;
- modifier setup.

But:

DO NOT attempt to generate the entire final body with a crude procedural formula.

Python should assist the artist/modeling workflow.

It must not replace geometric judgment.

====================================================================
25. GIT / CHECKPOINTS
====================================================================

Commit milestones:

01-reference-calibration
02-curve-cage
03-body-blockout
04-silhouette-validation
05-surface-refinement
06-panels-glass
07-front-rear-details
08-wheels
09-final-topology
10-materials-presentation
11-glb-html
12-final-validation

Do not hide failures.

If validation is bad:
document it and fix it.

====================================================================
26. HARD STOP CONDITIONS
====================================================================

STOP and FIX before continuing if:

- SIDE silhouette obviously differs from reference;
- roof profile is wrong;
- wheelbase is wrong;
- wheel arches are not real geometry;
- windshield angle is wrong;
- rear taper is wrong;
- body looks like a generic capsule;
- wireframe does not follow actual topology;
- doors/windows are only drawn lines;
- 3/4 render looks unlike the target;
- HTML viewer geometry differs from Blender geometry.

Absolutely DO NOT say "complete" if any of these are true.

====================================================================
27. DEFINITION OF DONE
====================================================================

The task is DONE only when:

[ ] FRONT matches reference
[ ] SIDE matches reference
[ ] REAR matches reference
[ ] TOP matches reference
[ ] perspective looks like same car
[ ] wheel centers / wheelbase correct
[ ] wheel arches modeled
[ ] greenhouse modeled
[ ] panel structure modeled
[ ] headlights / taillights modeled
[ ] smooth reflective surfaces
[ ] topology flow visually clean
[ ] blue wireframe represents real mesh topology
[ ] Blender file clean and organized
[ ] GLB exported from Blender
[ ] HTML loads exact exported GLB
[ ] mobile viewer framing correct
[ ] validation renders saved
[ ] documentation saved
[ ] git working tree clean

====================================================================
28. QUALITY PRIORITY
====================================================================

Priority order:

1. PROPORTIONS
2. SILHOUETTE
3. SURFACE QUALITY
4. FEATURE LINES
5. TOPOLOGY
6. PANEL STRUCTURE
7. EXTERIOR DETAILS
8. WHEELS
9. INTERIOR
10. PRESENTATION
11. HTML

DO NOT sacrifice items 1–5 to rush items 6–11.

====================================================================
29. IMPORTANT CONTEXT FROM PREVIOUS FAILED ATTEMPTS
====================================================================

Previous attempts failed because they did this:

multi-view silhouette
→ generic cross-sections
→ automatic loft
→ wireframe overlay

That produced a deformed "blob car".

DO NOT repeat it.

The correct workflow is:

multi-view reference
→ calibrated orthographic setup
→ semantic feature curves
→ transverse sections
→ validated 3D cage
→ controlled SubD/NURBS surface
→ silhouette validation
→ surface refinement
→ details
→ real mesh wireframe
→ GLB export
→ HTML viewer.

====================================================================
30. FIRST ACTION
====================================================================

Before modifying or generating geometry:

1. inspect all supplied reference images;
2. create the Blender project;
3. create calibrated FRONT/SIDE/REAR/TOP reference planes;
4. calculate normalized dimensions;
5. create docs/reference_dimensions.md;
6. render a screenshot showing all aligned reference planes;
7. only then begin CAGE modeling.

At the end of the first work cycle report:

REFERENCE CALIBRATION
- PASS / FAIL

DIMENSION TABLE
- length
- width
- height
- wheelbase
- wheel radius
- front overhang
- rear overhang

CAGE STATUS
- not started / partial / complete

VALIDATION
- FRONT
- SIDE
- REAR
- TOP

Do not claim the vehicle is modeled before actual Blender geometry exists.