# ADR 0004 — Three.js preview, Blender authoritative

Status: selected architecture baseline for review; implementation pending.

## Context

Authors need immediate 3D feedback while marking references and adjusting a
cage. A browser renderer can show this feedback, but duplicating Blender/core
surfacing, AUTO handles or final topology would introduce disagreement.

## Decision

Use Three.js for world axes, wheel/axle guides, landmarks, cage curves, sections,
coarse patch feedback and verified GLB display. Backend core services supply
samples/projections. Three.js owns cameras, selection, ray/gizmo interaction and
rendering. Blender owns final generated surfaces, topology, normals, materials,
render evidence and export. No Blender runtime runs in-browser.

AUTO-handle curves without Blender-derived samples appear as labelled control
polygons/approximations. A coarse patch is not a final surface. Built topology
wire comes from actual mesh edges; observed/inferred splines have separate styles.
The editor always shows the preview/artifact revision and stale state.

## Alternatives

Running Blender in-browser is outside scope. Reimplementing Coons/PCHIP and all
surface/detail generation in TypeScript would create a competing engine. Using
only static Blender renders would make basic authoring feedback too slow. The
selected split supports fast interaction with one authoritative compiler.

## Consequences and verification

Add generic core sampling where missing, without web dependencies. Test that
moving one point updates all projected views and that the browser loads only the
GLB verified for the selected run. Supported inspection modes consume built
artifacts; a smooth preview cannot certify Class-A or game-ready output.

See [UI](../studio_ui_spec.md) and [architecture](../studio_architecture.md).
