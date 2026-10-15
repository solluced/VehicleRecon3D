# EV surface reconstruction

Open **tesla_surface_model.blend** in Blender, or double-click **exports/viewer.html** for the interactive model. The HTML embeds the exact exported GLB and works offline without a server or installation. It requires WebGL 2.

The Blender project contains 53 semantic curves, four packed calibrated reference planes, five cameras, separate SubD body patches, doors, glass, real lamp/intake openings, arch returns, ten-spoke wheels and a basic interior. BODY_MASTER is the exterior assembly root. WIRE objects display actual control-mesh edges on the refined surfaces.

The physical scale assumes 4.8 m overall length. The supplied illustrative views have documented inconsistencies; see docs/reference_dimensions.md. Validation masks are manual traces of the supplied image, with fixed-camera comparison and no independent fit per view.

See **validation/perspective.png** for the studio render and **docs/validation_summary.md** for results. Exterior/glass control meshes are 99.81% quads. GLB geometry and desktop/mobile controls were verified. Browser lighting approximates the Blender materials; its geometry comes entirely from the GLB.

All scripts use Blender's bundled Python/NumPy or standard Python/Node modules. Rebuild and inspection instructions are in docs/modeling_notes.md. MANIFEST.sha256 covers the delivered project; docs/input_archive_MANIFEST.sha256 preserves the original archive manifest.
