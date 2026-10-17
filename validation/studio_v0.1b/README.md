# VehicleRecon Studio v0.1B release validation

Manual 2D authoring vertical slice: **PASS**. Implementation commit
`489d0c88b7d3aa347966ee90a6fce559e796ee33`; later commits contain documentation/evidence only.
The final evidence commit is recorded in Git history and the delivery response.

Launch: `vehicle-recon studio --root F:/T/projects`.
See [installation/development](../../docs/studio_development.md) and
[user manual](../../docs/studio_user_manual_v0.1b.md).

## Tests and roundtrip

| Gate | Result |
| --- | --- |
| Complete Python core + optional backend | 259 passed, 0 failures |
| Isolated core-only environment (no Studio/FastAPI/Uvicorn/PIL) | 222 passed; 5 heavy tests deselected |
| Frontend behavioral tests and TypeScript/Vite build | 22 passed |
| Real Edge browser authoring / laptop DPR 2 / dense workload | 3 passed; 0 flaky or skipped |
| Original 4K bytes, IDs, geometry, settings, revision through refresh/restart | PASS |
| Installed core + Studio wheel, packaged static assets and authenticated API | PASS |
| Two clean frontend builds, pinned npm lockfile | Identical asset bytes |
| Cold Tesla without cache | 14/14 PASS; GLB, manifest, desktop/mobile viewer PASS |
| Protected Tesla / Mark II / frozen fixtures diff from phase base | Empty |

The CLI test exercises a real ephemeral loopback HTTP service, browser bootstrap
callback and graceful shutdown while SSE is active. Browser tests use test-owned
servers/contexts, temporary analytical fixtures and actual production UI controls.
They cover point creation/drag/deletion, curves/knots, typed settings/provenance,
core undo/redo, external revision conflict, SSE reconnect, refresh and restart.
There is no test-only geometry endpoint. The package check imports the installed
wheels and their schema resources rather than the editable source tree.

## Measured performance

Analytical 3840×2160 PNG, 5000 canonical points, 20 independently configured
logical layers (two physical Konva canvases), 1500×1000 viewport, DPR 1,
Edge 155 headless, Ryzen 7 5800X / 16 logical CPUs / 32 GiB RAM.
Scripted pointer/wheel input goes through production Konva handlers; eight
canonical property edits use the visible UI. These are measurements on this
machine, not a hardware-independent FPS guarantee.

| Measurement | Result |
| --- | --- |
| First editor display | 876 ms |
| Pan frame p95 / measured FPS | 10.7 ms / 123.9 |
| Zoom frame p95 / measured FPS | 13.5 ms / 111.7 |
| Pan / zoom draw p95 | 1.9 / 1.8 ms |
| Drag frame p95 | 8.8 ms |
| Picking / visible selection p95 | 0.1 / 13.8 ms |
| Commit + canonical verification p95 | 3389 ms |
| JS heap before → after GC, eight edits | 6.44 → 11.17 MiB |
| Backend RSS before → after, eight edits | 78.96 → 212.94 MiB |

Local manipulation meets the suggested near-60-FPS target in this run.
Canonical save/validation/readback remains synchronous and can take several
seconds at this density. The memory window includes lazy inspector creation,
live undo history and bounded idempotency responses; it does not prove absence
of long-session leaks. Full samples/environment are in [performance.json](performance.json).
The structural-validation optimization has separate before/after evidence and
validator-equivalence/cache-invalidation tests; semantic checks always rerun.

## Tesla and Mark II

Tesla IoU: SIDE **0.957230**, TOP **0.936083**, FRONT **0.931202**,
REAR **0.944724**. Fresh GLB positions/normals/indices/nodes match the published
accepted output exactly; UV maximum difference is **5.960464477539063e-08**
(one float32 ULP). All eight proof PNGs are byte-identical. Blender's frozen
control/topology check passed. The accepted explicit review was reused only
because its actual proof/config hashes remain valid; no review was invented.
The existing published projects/fixtures were never rewritten by this release.

Mark II remains **INCONSISTENT_SOURCE**, existing cage **FAIL**, surfaces and
details **NOT STARTED**; rejected rectification remains inactive. All nine
protected SHA-256 checks pass. Studio completion describes the authoring tool,
not completion of either vehicle asset.

## Definition of Done

- [x] CLI launch
- [x] Local browser UI
- [x] Security baseline
- [x] Project browser
- [x] v2 create/open
- [x] v1 read only
- [x] Original image bytes
- [x] 4K image
- [x] Pan
- [x] Pointer centered zoom
- [x] Fit and actual pixels
- [x] Layers
- [x] Point add/select/move/delete
- [x] Polyline and spline controls
- [x] Semantic role editing
- [x] Properties
- [x] Schema settings
- [x] Typed dimension provenance
- [x] Core undo/redo
- [x] Revision conflicts
- [x] External conflict
- [x] Readiness and stale state
- [x] Canonical roundtrip
- [x] Close and reopen
- [x] Browser E2E
- [x] One canonical geometry model
- [x] No raw file write endpoint
- [x] No CV required
- [x] No LLM required
- [x] No Blender build for authoring
- [x] Independent core install
- [x] Tesla unchanged
- [x] Mark II untouched

## Reproduction and limits

```powershell
python -m pip install -e ".[test]" -e "studio/backend[test]"
python -m pytest tests studio/backend/tests -q
cd studio/frontend
npm ci
npm run build
npm test
npm run e2e
```

Heavy release command from the repository root:
`python -m vehiclerecon run build/studio-v01b-tesla-cold --no-cache`.
Its isolated seed contains the published Tesla project.json, input/, generated/
and existing explicit review only. Blender/runtime paths use the existing generic
environment configuration. After the run the frozen delivered .blend is checked
with the generic Blender `regression` adapter. See the copied pipeline and
control reports. The core-only CI job excludes Blender/integration markers.

[Remote CI run 39015012197](https://github.com/solluced/VehicleRecon3D/actions/runs/39015012197)
passed all four separate jobs (core, backend, frontend and real Chromium browser)
on the exact implementation commit. See [ci.json](ci.json). The heavy Blender
Tesla run is a separate local release gate. Python has one nonfailing
Starlette/httpx test-client deprecation.

Not implemented: Three.js 3D authoring, CV, Smart Edge, Magic Select,
rectification UI, surface graph editor, full Blender Render button, independent
Bezier tangent editing. Live history/idempotency restart persistence and
long-session memory certification are outside this slice. Blockers: **none**.

Screenshots: [desktop](desktop.png), [laptop/DPR 2](laptop_dpr2.png),
[4K/5000/20 layers](performance.png). Every source record is canonical data;
the displayed grid/points are analytical test data, not an inferred vehicle.
