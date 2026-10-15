# Modeling notes

The existing Blender starter contains scene/bootstrap structure and no accepted vehicle geometry. The previously missing reference images are now bundled under `refs/`.

Continue from `tesla_surface_model.blend` and follow `PRODUCTION_HANDOFF.md`:

1. inspect all bundled references;
2. calibrate reference planes and cameras;
3. build sparse semantic longitudinal curves and transverse sections;
4. validate the 3D cage in SIDE/TOP/FRONT;
5. build controlled SubD/NURBS-like automotive surfaces;
6. validate silhouettes and curvature before details;
7. export GLB only after validation;
8. HTML must load the exact Blender-exported GLB.

Do not use a generic procedural body, guessed dimensions, fake validation, or decorative wireframe unrelated to actual topology.
