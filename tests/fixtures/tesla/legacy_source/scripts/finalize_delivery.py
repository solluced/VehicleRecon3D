"""Verify the delivered file set, write documentation and final checksums."""
from pathlib import Path
import json,hashlib,shutil,base64,re
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def write(path,text):(ROOT/path).write_text(text,encoding='utf-8',newline='\n')
r=read('validation/report.json');audit=read('validation/geometry_audit.json');g=read('validation/glb_geometry_report.json');qa=read('validation/viewer_qa.json');exp=read('exports/export_manifest.json')
assert r['silhouette_pass'] and r['surface_quality_pass'] and g['status']=='PASS' and qa['status']=='PASS'
assert r['source_blend_sha256']==exp['source_blend_sha256']==g['source_blend_sha256']==digest('tesla_surface_model.blend')
assert qa['glb_sha256']==exp['glb_sha256']==g['glb_sha256']==digest('exports/tesla_surface_model.glb')
html=(ROOT/'exports/viewer.html').read_text(encoding='utf-8')
embedded=re.search(r'const GLB_BASE64="([A-Za-z0-9+/=]+)"',html).group(1)
assert hashlib.sha256(base64.b64decode(embedded)).hexdigest()==g['glb_sha256']
for entry in read('refs/manifest.json'):assert digest(entry['file'])==entry['sha256']
required=['tesla_surface_model.blend','exports/tesla_surface_model.glb','exports/viewer.html',*[f'validation/{v}.png' for v in ('front','side','rear','top','perspective')],'validation/report.json','docs/reference_dimensions.md','scripts/setup_reference.py','scripts/validate_silhouette.py','scripts/export_glb.py','scripts/render_validation.py']
assert all((ROOT/p).is_file() and (ROOT/p).stat().st_size for p in required)
quad=audit['surface_control_mesh']['quad_percent']
views='\n'.join(f"| {v.upper()} | {r['views'][v]['iou']:.4f} | {r['views'][v]['threshold']:.2f} | PASS |" for v in ('side','top','front','rear'))
write('README.md',f'''# EV surface reconstruction

Open **tesla_surface_model.blend** in Blender, or double-click **exports/viewer.html** for the interactive model. The HTML embeds the exact exported GLB and works offline without a server or installation. It requires WebGL 2.

The Blender project contains 53 semantic curves, four packed calibrated reference planes, five cameras, separate SubD body patches, doors, glass, real lamp/intake openings, arch returns, ten-spoke wheels and a basic interior. BODY_MASTER is the exterior assembly root. WIRE objects display actual control-mesh edges on the refined surfaces.

The physical scale assumes 4.8 m overall length. The supplied illustrative views have documented inconsistencies; see docs/reference_dimensions.md. Validation masks are manual traces of the supplied image, with fixed-camera comparison and no independent fit per view.

See **validation/perspective.png** for the studio render and **docs/validation_summary.md** for results. Exterior/glass control meshes are {quad:.2f}% quads. GLB geometry and desktop/mobile controls were verified. Browser lighting approximates the Blender materials; its geometry comes entirely from the GLB.

All scripts use Blender's bundled Python/NumPy or standard Python/Node modules. Rebuild and inspection instructions are in docs/modeling_notes.md. MANIFEST.sha256 covers the delivered project; docs/input_archive_MANIFEST.sha256 preserves the original archive manifest.
''')
write('docs/modeling_notes.md',f'''# Modeling notes

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
The exterior/glass control meshes contain {audit['surface_control_mesh']['faces']} faces, {quad:.2f}% quads. Small welded frame corners account for the remaining triangles; broad hood, roof and door patches retain quad flow. Geometry checks found finite coordinates and no zero-area faces after corner cleanup. Open panel and aperture edges are intentional parts of the surface assembly.

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
''')
write('docs/validation_summary.md',f'''# Final validation

Reference registration: **PASS with documented source inconsistencies**. Cage: **complete**, 53 semantic curves. Original five reference images verified unchanged. The normalized ratios and assumed 4.8 m scale are documented in reference_dimensions.md.

| View | IoU | Suggested threshold | Result |
| --- | ---: | ---: | --- |
{views}

These are actual opaque geometry renders from the fixed calibrated cameras, compared with manual source-image traces including tires and mirrors. No per-view bounding-box fitting is performed. End views use the declared reference rectification. Pixel mismatch and bounding-box deltas are in validation/report.json; colored comparisons are under validation/masks/ (red = reference only, blue = model only).

Surface review: **PASS for visual SubD presentation**, using studio, reflection-coordinate stripes and Workbench car-paint matcap. The review and proof hashes are recorded in validation/surface_review.json. This is not a numerical G2 certificate.

Topology: **{quad:.2f}% quads**, with finite coordinates and no zero-area faces. See validation/geometry_audit.json. Wheelbase from actual wheel roots: **{audit['wheelbase_m']:.6f} m**. The evaluated body envelope is approximately 4.807 × 1.882 m, with roof height about 1.524 m above ground; the small difference from the chosen envelope comes from subdivision and surface roll.

GLB: **PASS**, {g['mesh_nodes']} mesh nodes and {g['triangles']:,} triangles including the topology overlay. Every exported node matches the evaluated Blender triangle count and world bounds within 0.1 mm. See validation/glb_geometry_report.json. The HTML embeds the exact GLB bytes, verified by SHA-256.

Viewer: **PASS** at 1440 × 1000 desktop and 390 × 844 mobile. Browser tests exercised all five presets, automatic framing, fit/reset, four layer toggles, mouse drag, wheel zoom and two-finger pinch. No WebGL errors were recorded. See validation/viewer_qa.json and viewer_desktop.png / viewer_mobile.png.

Scope limits: physical length is assumed; cross-view source conflicts are reconciled rather than concealed. Interior and lamp optics are simplified. Blender materials and browser lighting differ, while exported geometry is shared exactly. The saved model is a panel/SubD assembly, suitable for continued surface editing and presentation.

Required files, source/export hashes and the exact embedded GLB are checked by scripts/finalize_delivery.py. Local Git milestone history is retained; final working-tree status is checked after the delivery commit.
''')
dimensions=(ROOT/'docs/reference_dimensions.md').read_text(encoding='utf-8-sig')
if '## Greenhouse reconciliation' not in dimensions:
    dimensions+='''\n## Greenhouse reconciliation
The top-view roof footprint suggests a wider upper greenhouse than the rectified end views. Roof-edge half-width was reconciled to approximately 0.61–0.62 m through the B-pillar zone, widening to about 0.74 m at the windshield base; window sills are about 0.73 m from center. The side roof profile remains authoritative vertically. Mirror housings use an approximately 1.905 m total envelope because top/end mirror projection disagrees. These choices are inferences from adjacent primary views, not independent dimensional claims from the quality target.
'''
write('docs/reference_dimensions.md',dimensions)
write('docs/development_log.md','''# Development evidence

The previous starter had no images; the continuation package supplied all five. Their existence, decoded dimensions and original hashes were verified before geometry work.

The first cage overlay showed square nose/tail sections in plan view. Those sections were narrowed and the shoulder rails reconciled. The first body mask comparison measured side 0.8975, top 0.9254, front 0.8941 and rear 0.9047 IoU. Wheelhouse backing, window-frame joins, front lip and greenhouse registration were corrected before further detailing.

Reflection inspection exposed cowl/rear-quarter interpolation overshoot. Shape-preserving tangents and controlled transverse fender roll replaced the offending interpolation. The first detailed headlights were too vertical; they were moved to the cheek patches. Rims were inset into the tire profile and brake discs moved behind the spokes.

A refinement script initially assumed vertex indices survived a cleanup weld. It raised IndexError and prevented later presentation objects from being created. The cowl update now rebuilds its control grid, the bridge is integrated into the fender boundary, and Blender commands use --python-exit-code 1. The corrected pipeline completed without Python exceptions and the saved project contains all 24 topology overlays.

Browser screenshots exposed incorrect canvas alpha composition, which was corrected to an opaque neutral canvas with transparent glass rendered over it. Rear lamp returns were seated against the evaluated hatch surface after a final screenshot showed one standing proud. Geometry checks, renders, exports and browser QA were regenerated after these corrections.

Intermediate diagnostic logs remain locally under validation/*.log and are excluded from Git. The final structured reports and proof renders are tracked.
''')
if not (ROOT/'docs/input_archive_MANIFEST.sha256').exists():shutil.copyfile(ROOT/'MANIFEST.sha256',ROOT/'docs/input_archive_MANIFEST.sha256')
r.update(status='validated_deliverables',complete=True,export_allowed=True,
    glb_geometry_report='glb_geometry_report.json',viewer_qa='viewer_qa.json',
    artifact_checks={'required_files_present':True,'original_reference_hashes_match':True,'blend_export_hashes_match':True,'html_embeds_exact_glb':True,'browser_controls_and_mobile_framing_pass':True})
write('validation/report.json',json.dumps(r,indent=2)+'\n')
# Keep text bytes reproducible across checkouts; binary assets remain unchanged.
files=[]
for folder in ('docs','refs','scripts','validation','exports'):
    files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.log')
files.extend(ROOT/p for p in ('README.md','START_HERE.md','PRODUCTION_HANDOFF.md','.gitignore','.gitattributes'))
for p in files:
    if p.suffix in ('.py','.mjs','.md','.txt','.json','.html','.sha256') or p.name in ('.gitignore','.gitattributes'):
        text=p.read_text(encoding='utf-8-sig').replace('\r\n','\n');p.write_text(text,encoding='utf-8',newline='\n')
files.append(ROOT/'tesla_surface_model.blend')
lines=[hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix() for p in sorted(set(files),key=lambda p:p.relative_to(ROOT).as_posix())]
write('MANIFEST.sha256','\n'.join(lines)+'\n')
print(json.dumps({'status':'DELIVERY_FILES_VERIFIED','files_in_manifest':len(lines),'quads_percent':quad,'iou':{k:v['iou'] for k,v in r['views'].items()}},indent=2))
