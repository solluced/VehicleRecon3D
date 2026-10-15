# START HERE — Tesla Surface Model Production Pass

This package is the continuation of the existing Blender starter. The previous work cycle stopped correctly because the image references were missing. **They are now bundled in `refs/`.**

## Immediate task

1. Read `PRODUCTION_HANDOFF.md` completely.
2. Verify all five images listed in `refs/README.md` can be opened.
3. Open `tesla_surface_model.blend`; do not replace it with a generic procedural body.
4. Calibrate FRONT / SIDE / REAR / TOP references into one coordinate system.
5. Update `docs/reference_dimensions.md` with measured normalized ratios and chosen physical scale.
6. Save an alignment proof render/screenshot under `validation/reference_alignment.png`.
7. Build the **semantic 3D curve cage** before creating the final body surface.
8. Validate cage silhouettes in SIDE, TOP and FRONT before detailed surfacing.

## Important

The clean blue wireframe image is the **quality target**, while `reference_multiview.png` is the **geometry source of truth**.

Do not recreate the previous failed pipeline:

`silhouette -> generic sections -> lofted blob -> decorative wireframe`

Required pipeline:

`calibrated multiview -> semantic feature curves -> transverse sections -> validated 3D cage -> controlled SubD/NURBS surface -> validation -> details -> exact GLB export -> HTML viewer`

The project is not complete until the definition-of-done in `PRODUCTION_HANDOFF.md` is satisfied.
