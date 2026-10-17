# VehicleRecon Studio v0.1B — manual authoring

Launch from your installed repository:

```powershell
vehicle-recon studio --root F:/T/projects
```

The browser opens a local authenticated workspace. Leave the terminal running;
Ctrl+C closes the service. See [developer installation](studio_development.md)
if the optional Studio package is not installed.

## Create or open

Select a project on the home screen, or create a new study using a safe project
name and an existing vehicle profile. New projects are v2 DRAFTs. Known dimensions
are optional and expressed in metres; blanks remain unknown. Creation-time values
are marked approximate until you supply their authority in Settings.

Legacy v1 projects are visible and readable, labelled READ ONLY. Opening one
does not migrate it. The v2 manual editor has no migration button; use the core
CLI's explicit backed-up migration on a separate copy when you intend to migrate.

## Import and navigate

Drop a reference into an empty editor or choose **Import reference**. PNG and
JPEG are supported within the displayed import budgets. Existing configured
references are available in the reference picker. Imports preserve original
bytes. A role already assigned to a multiview image is not silently replaced.
Upright source images are required; rotated EXIF imports show an error.

Choose FRONT, SIDE, REAR or TOP to tag the observation view. These tabs do not
calibrate or reinterpret a multiview sheet. In this phase the canvas displays
original source pixels, with no inferred metric mapping or world geometry.
Changing source or view cancels an unfinished curve gesture.

| Action | Input |
| --- | --- |
| Pan | Pan tool, middle drag, or Space+drag on canvas |
| Zoom at pointer | Mouse wheel |
| Zoom controls | + / − buttons or keyboard |
| Fit image | Fit or F |
| Actual pixels | 1:1 or 1; one source pixel per device pixel |
| Reset viewport | Reset view (fit) |
| Cancel gesture | Escape |

The canvas follows the viewport and device pixel ratio. Navigation and opacity
are presentation changes, outside geometry undo history.

## Layers and observations

Source Image has a permanent content lock and adjustable visibility/opacity.
Observations, Source Curves, and Landmarks / Datums have visibility, lock and
opacity controls. Lock permits inspection while preventing edits. Hiding a layer
never removes its validation checks. Additional display layers and assignments
are presentation preferences, not new vehicle geometry.

Choose **+ Point**, select a role from the current core profile, then click the
source. Select an observation using its canvas control or entity list. Drag an
unlocked control to move it; one MoveObservation command commits at release.
Delete entity removes a selected point. Source coordinates are never world XYZ.

Choose **Polyline** or **Spline**, place at least two knots, then press Enter or
Finish curve. Source splines store explicit initial Bezier handles. Select a knot
to drag or delete it; + Knot inserts after the selected knot (or appends when
only the curve is selected). Delete curve removes the complete source curve.
Split at knot requires an interior knot. Merge is available only for compatible
curves sharing the same stable endpoint; other merges remain unavailable.
Independent tangent-handle editing is deferred.

Use Properties to search/select a semantic role and edit view, pixel position,
uncertainty, provenance, visibility and measured state. ID and source identity
are read-only. Apply properties persists one typed operation/batch. Inferred
observations are not marked measured. Existing bindings or authoritative locks
may reject an edit; the error explains the affected entity rather than silently
rebinding it. Core profile roles are the only semantic vocabulary.

## Settings, saving and history

Settings generates basic controls from the canonical project schema. It exposes
asset name, vehicle profile, DRAFT/READY state and nullable dimensions. Dimension
entries include typed official/measured/inferred/approximate provenance, method,
citation and optional uncertainty. Apply settings uses the same core service.
Selecting READY cannot bypass missing data or authoring reviews.

Commands persist transactionally immediately after creation, drag end or Apply.
There is no separate delayed geometry save store. Saved means the last command
completed; an unfinished form or curve gesture must still be applied/finished.

Use toolbar Undo/Redo, Ctrl+Z and Ctrl+Shift+Z. Canonical history comes from the
core live authoring session. Browser refresh can reconnect to that live history;
restarting the backend begins a new history session while preserving saved files.

Revision, save state and readiness remain visible. References, calibration,
source review, cage, cage review and surfaces report core states/reasons. A new
manual draft normally has blocked calibration/reviews/cage/surfaces. Successful
point creation does not mean source or cage acceptance.

## Conflicts and reopen

An external edit or stale revision stops the write and displays Conflict. Use
Reload canonical state to inspect the current files and start a new history
branch. There is no automatic merge or overwrite. Another editor tab may hold
the lease; close/leave it or wait for expiry, then reload. A failed drag displays
the canonical position again. Technical details are expandable separately from
the primary error.

Close Studio, launch again and select the same project. Saved entities, stable
IDs, coordinates, settings and revision are reconstructed from canonical files.
Viewport/layers are saved separately in `.studio/session.json` on a best-effort
basis. Deleting that file removes preferences, not authoring data.

## Scope

v0.1B provides manual 2D source authoring only. There is no Three.js world editor,
CV/Smart Edge/Magic Select, rectification editor, surface graph editor or Blender
Render button. No LLM, model download or Blender build is required to author.
Mark II's inconsistent-source rejection and unstarted surfaces/details remain
unchanged. This editor does not claim a completed or game-ready vehicle asset.
