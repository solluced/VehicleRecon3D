# VehicleRecon3D 0.1

Reference-constrained automobile reconstruction using declarative calibration,
semantic curves, boundary-controlled quad/SubD surfaces and reusable detail
components. Vehicle geometry lives in `projects/<id>/`, not framework Python.

The supplied integration project is `projects/tesla`. Its accepted reference
scale and illustrative-sheet inconsistencies are preserved. v0.1 proves the
Tesla extraction; portability to another vehicle is reserved for later work.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python -m vehiclerecon inspect projects/tesla
python -m vehiclerecon run projects/tesla
python -m pytest
```

Requires Python 3.11+, Blender (tested with 5.2.2 LTS), Node and Chromium/Edge for
the required browser regression. Set `VEHICLERECON_BLENDER` and
`VEHICLERECON_BROWSER` if discovery needs an explicit executable.

Open `projects/tesla/output/tesla_surface_model.blend`, or the self-contained
`projects/tesla/output/viewer.html`. The viewer embeds the exact verified GLB.
Validation evidence and stage results are under `projects/tesla/validation/`;
the project delivery manifest is `projects/tesla/output/delivery_manifest.json`.

A missing or stale explicit visual review blocks presentation acceptance and
export. Inspect the proof renders, then record an actual decision:

```powershell
python -m vehiclerecon review projects/tesla --reviewer "Your name" --decision PASS --note "What was inspected and accepted" --limitation "Known limitations"
python -m vehiclerecon run projects/tesla
```

Review is never inferred from script execution. Required gate failures return a
nonzero exit. Cache skips verify output hashes; `run --no-cache` forces a full
reconstruction. `init` creates an incomplete authoring draft with unmeasured
dimensions; it does not invent a new vehicle or automatically solve semantics.

See [architecture](docs/architecture.md), [project format](docs/project_format.md),
[inference standard](docs/inference_standard.md), [pipeline](docs/pipeline.md)
and [adding a vehicle](docs/adding_a_vehicle.md).

The local visual editor is documented in the
[VehicleRecon Studio architecture baseline](docs/studio_architecture.md) and
[implementation roadmap](docs/studio_roadmap.md). The
[v0.1A core authoring foundation](docs/core_authoring.md) implements v2 contracts,
typed editing, atomic recovery, acceptance gates and managed jobs.
**Studio v0.4** preserves coordinated views, correspondences, explicit world landmarks,
fit proposals, residual heatmaps/reviews and a live Three.js cage preview. It adds
optional local Smart Edge, Magic Select, contour and wheel proposals to the
authenticated FastAPI + React/TypeScript/Konva source editor. Reference → Rectification
adds manual anchors, core mapping/scale graphs, independent held-out validation,
candidate comparison, explicit activation/undo and safe source replacement:

```powershell
python -m pip install -e studio/backend
vehicle-recon studio --root projects
```

Open/create v2 drafts, import original images, edit points/curves/properties,
undo/redo and reopen canonical files. V1 stays read-only in Studio and runs
unchanged through the CLI. Node and Blender are not needed for normal manual
authoring; prebuilt assets ship with the optional distribution. See
[installation/development](docs/studio_development.md) and the
[v0.4 user manual](docs/studio_user_manual_v0.4.md). Install the CPU-only baseline
with `python -m pip install -e "studio/backend[cv]"`, or keep using manual tools
without it. CV proposals require inspection and explicit ACCEPT into source
observations; they do not move world geometry. Surface editing and Studio Blender
build orchestration remain deferred.

The accepted baseline remains frozen in `tests/fixtures/tesla/baseline/`.
The original 91-file Tesla project, including its coupled Python scripts, is
archived byte-for-byte in `tests/fixtures/tesla/legacy_source/` for regression
evidence. Production code has no dependency on that archive. FBX is not an
implemented/tested v0.1 capability; GLB is the validated interchange format.
