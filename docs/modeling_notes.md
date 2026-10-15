# Modeling notes

## Source and construction
Built in Blender 5.2.2 LTS, using the original supplied starter. Original references were decoded and SHA-256 verified. The multiview image controls geometry; the surface target and workflow control presentation and topology intent. The two annotated references guide semantic coverage only.

Reference calibration preceded the curve cage, which preceded any body mesh. The retained cage has 53 Bezier curves covering L00–L15, T00–T13, tires and arches. Controls occur at crown, pillar, axle, shoulder, rocker and bumper events. The body uses independent, authored boundary-controlled quad patches and arch annuli. Hood and greenhouse longitudinal boundaries read the semantic cage; authored sectional and transverse tangent constraints control the surface roll. The body is not a whole-car silhouette loft.

Front and rear fenders have geometric wheel openings, returns and recessed wheelhouses. Shape-preserving C1 interpolation suppresses curve overshoot. The cowl bridge joins the actual fender boundary to the hood shoulder. Mirror symmetry is retained where useful; individual doors and side glass remain separate meshes. Viewport subdivision is 1 and render subdivision 2 on main panels. Thickness is modeled with Solidify.

## Components
- DOOR_FL/FR/RL/RR, HOOD, REAR_HATCH and hatch top are separate panel meshes. Door edges are separated at approximately 3 mm; inner backing skins and separate flush handles are geometry.
- Windshield, panoramic roof, rear glass and all four side windows are separate. Pillar, roof-rail, sill and window-frame geometry defines their boundaries.
- Headlamp, central intake, side intake, rear lamp and diffuser openings delete actual body faces and retain recessed mesh housings. Rear lamp returns are fitted to the evaluated hatch surface. Grille slats, LED strips and diffuser fins are geometry.
- WHEEL_FL/FR/RL/RR are assembly roots. Tires use shared annular profile data, with separate rim lips, ten swept spokes, hubs, lugs and recessed brake discs.
- The interior includes front seats/headrests, rear bench/backrest, dashboard, display, steering wheel, console and floor.

## Topology and presentation
The exterior/glass control meshes contain 3693 faces, 99.81% quads. Small welded frame corners account for the remaining triangles; broad hood, roof and door patches retain quad flow. Geometry checks found finite coordinates and no zero-area faces after corner cleanup. Open panel and aperture edges are intentional parts of the surface assembly.

Each WIRE object copies the real control mesh, follows its refined source surface and uses the Wireframe modifier. The source_topology_object property records its origin. There is no independently drawn decorative grid. SCENE_PRESENTATION uses a front-left orthographic 3/4 camera, neutral studio lighting and a shadow ground. Original images and cropped plane textures are packed.

## Validation and interpretation
Inspect validation/perspective_surface.png, surface_reflections.png and surface_matcap.png. Reflection continuity was reviewed on the hood/roof, fender crowns, door centers, pillars and quarters. Panel gaps and styling feature transitions intentionally interrupt reflections. This is a visual SubD reconstruction of an illustrative sheet; numerical G2/manufacturing certification and OEM dimensions are not asserted.

Source ambiguities include inconsistent front/rear aspect ratios, greenhouse half-width, side-view tire sizes and mirror projection. End-view registration and the chosen compromises are explicit in reference_dimensions.md. Silhouette IoU concerns the traced exterior projection, not internal styling accuracy.

## Rebuilding
Work on a copy or a new Git branch before regenerating. Use Blender background mode with **--python-exit-code 1** so exceptions stop the pipeline. From the project root, run the relevant scripts in this order:

1. setup_reference.py; build_cage.py
2. build_surfaces.py; validate_silhouette.py
3. After the basic silhouette passes: build_details.py; refine_final.py; fit_lamp_returns.py
4. presentation.py; audit_geometry.py; inspect_surface.py; render_matcap.py; render_validation.py
5. finalize_scene.py; validate_silhouette.py
6. Inspect all renders, then record_surface_review.py using ordinary Python.
7. export_glb.py in Blender; verify_glb.py and build_viewer.py using ordinary Python.
8. test_viewer.mjs with Node and an isolated headless Chromium DevTools session on localhost:9333; finalize_delivery.py after QA.

For example: `blender --background tesla_surface_model.blend --python-exit-code 1 --python scripts/render_validation.py`. Review acceptance is deliberately separate from the automated mask test. Export refuses an unreviewed or stale Blender file. Curve conversion occurs only in the in-memory export session; the saved project retains editable curves.

The local viewer is dependency-free. Its geometry is parsed directly from the embedded GLB. Browser glass uses an alpha approximation of transmission; studio lighting differs from Cycles. The Blender file and standalone GLB remain available for a renderer with full glTF material support.
