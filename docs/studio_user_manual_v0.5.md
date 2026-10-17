# VehicleRecon Studio v0.5

Open a v2 authoring study and select **Surfaces**. Keep the source and cage reviews
current. A blocked source/cage state disables preview; accepting a draft graph does
not accept its source evidence. Legacy projects, including Mark II, remain read-only.

1. Choose a core operation, name and semantic role, then **Add patch draft**.
   The stable patch/sample IDs appear in the patch list and dependency DAG.
2. Select the patch. For Coons, assign bottom, top, left and right. Choose an existing
   derived curve or eligible cage rail from a boundary selector; alternatively click
   a curve in 3D, then **Use picked** for the desired slot. Use **Add derived node
   draft** to author an existing curve/offset operation and fill its typed parameters.
3. Check arrows and the expected corner correspondence. **Reverse** changes only
   that input's orientation. Complete required parameters and **Mark node complete**.
   Incomplete drafts save safely but cannot execute. A cycle or invalid reference
   stays an unsaved invalid draft; correct it or **Discard invalid draft**.
4. Choose low/medium resolution and **Generate coarse preview**. Inspect individual
   corner gaps and the validation panel. A corner mismatch fails rather than snapping
   geometry. The preview reports operation, resolution and canonical revision.
5. Switch **Wireframe · preview topology**, face/sample normals and patch color modes.
   Wire edges belong to the actual current preview mesh. Click a mesh to select its
   canonical patch; patch list, properties and DAG share stable selection.
6. Inspect adjacency maximum/RMS gaps and normal angles. Use **Declare adjacency**
   to connect explicit edges and set their correspondence/tolerance. Click a failed
   pair to select it and show the continuity heatmap. G1-like is a sampled diagnostic,
   not a strict continuity or Class-A guarantee.
7. Set U/V resolution, explicit support sample positions, Y=0 mirror and a material
   role where supported. Normal direction is an explicit world-space vector.
   Parameter forms come from the core operation schema; arrays contain numeric data.
8. **Undo** and **Redo** restore exact canonical graph bytes. Successful commands
   autosave immediately. Reload/reopen retains IDs, parameters and connectivity.

Source, cage, graph or calibration changes mark old preview STALE. Reinspect evidence
and renew stale source/cage reviews in the existing Multi-view workspace before
regeneration. Old diagnostic geometry may remain visible with a dashed stale frame;
it is not certified current. External edits stop writes until canonical reload.

The capability panel lists limitations. Previous patch edge extraction, AUTO-handle
boundaries and arbitrary mirror planes are not currently offered by the trusted
core operation set. Support strength/offset controls are not fabricated. Existing
arch/ribbon operations have their own actual control-scale/offset parameters.

Blender owns production geometry, final modifiers and audit. This release does not
add Render orchestration, final export or Cyberpunk import. Do not infer final mesh,
Class-A, self-intersection or game-readiness certification from the coarse preview.

See [surface contracts](surface_authoring.md) and the
[release evidence](../validation/studio_v0.5/README.md) for scope and measured checks.
