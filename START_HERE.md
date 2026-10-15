# START HERE — EV Surface Model Delivery

Open `tesla_surface_model.blend` for the editable model and studio presentation, or double-click `exports/viewer.html` for the offline interactive viewer. The viewer embeds the exact Blender-exported GLB.

## Review the result

1. Inspect `validation/perspective.png` and the four orthographic renders.
2. Read `docs/validation_summary.md` for measured results and verification limits.
3. Read `docs/reference_dimensions.md` for the assumed scale, raw landmarks and source conflicts.
4. In Blender, unhide `00_REFERENCE` objects or `01_CURVE_CAGE` to inspect registration and semantic controls. They are hidden for presentation renders.
5. Use `docs/modeling_notes.md` for component organization and the rebuild sequence.

## Important

The original five references remain in `refs/`, with verified original hashes. `reference_multiview.png` controls proportions; the surface target and workflow guide quality and presentation. Physical length is assumed at 4.8 m. The illustrative views require the documented reconciliation.

The retained modeling workflow is:

`calibrated multiview -> semantic feature curves and sections -> quad surface patches -> silhouette and reflection checks -> panel/aperture details -> real topology overlay -> exact GLB export -> offline viewer`

`PRODUCTION_HANDOFF.md` retains the original task specification. `docs/development_log.md` records failed intermediate checks and their fixes. `MANIFEST.sha256` covers the delivered files.
