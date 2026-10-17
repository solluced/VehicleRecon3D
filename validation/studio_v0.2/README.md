# VehicleRecon Studio v0.2 release validation

Multi-view consistency and live 3D cage: **PASS** against all 30 handoff criteria.
Implementation: `02d80b638aaa11e6ddab5c9cf17427a47f362d09`. Later commits contain documentation/evidence.
Final evidence commit is recorded in Git history and the delivery response.

Launch: `vehicle-recon studio --root F:/T/projects`.
[User manual](../../docs/studio_user_manual_v0.2.md) ·
[Development / reproducible profiles](../../docs/studio_development.md) ·
[Solver math](../../docs/multiview_fitting.md) · [Machine report](report.json).

## Verification

| Gate | Result |
| --- | --- |
| Complete Python core + optional backend | 277 passed |
| Isolated core without Studio/FastAPI/Uvicorn/PIL | 232 passed; 5 heavy deselected |
| Frontend behavioral tests / TypeScript / Vite | 32 passed / PASS / PASS |
| Real browser matrix | 7 passed; no failures, flaky or skipped |
| Local software-renderer portability scenarios | 2 passed; rendered-camera and visible-selection waits |
| Local software-renderer dense workloads | 2 passed; current form subject and complete refresh |
| Remote four-job CI | Core/backend/frontend/browser all PASS; see ci.json |
| Installed core + optional Studio wheels | PASS; all five current static files and solver schema |
| Repeated production frontend build | Identical bytes; pinned lockfile |
| Tesla cold release | 14/14 PASS; GLB and desktop/mobile viewer PASS |
| Protected Tesla/Mark II/frozen fixtures | Empty tracked diff from phase base; nine Mark II hashes match |

The browser workflow covers A–N from the handoff: four calibrated views,
binding/unbinding, observed versus projected markers, distinct source/world edits,
2D/3D selection, proposal ghost without mutation, apply/undo/redo, individual red
failures, source rejection, consistent source+cage acceptance, refresh/restart.
Additional cases exercise stale proposals after an external cage edit, native X
and XZ gizmo drags with one release transaction, a laptop at DPR 2, the retained
source editor and read-only Mark II conflicts. No test-only geometry endpoint.
The local full matrix used production checkpoint 554d099; subsequent changes
only synchronize test input with rendered camera/selection state and update
documentation. The two changed tests also pass locally with software rendering.
Remote CI runs all seven cases with the final harness and software renderer.
Its exact browser results and separate runner performance measurements are in
ci_browser_tests.json, ci_multiview_performance.json and
ci_source_editor_performance.json; those timings are not mixed with local ones.

## Measured performance

Windows / Edge 155 headless / Ryzen 7 5800X / 32 GiB / 1500×1000 DPR 1.
Four simultaneous 2D views, one Three.js view, 3840×2160 source, 5000 source
entities, 17 canonical landmarks and nine cage curves. Browser pointer/wheel
events pass through production handlers. Timings describe this machine/run,
not guaranteed FPS on other hardware. See multiview_performance.json.

| Measurement | p95 / result |
| --- | --- |
| First multi-view display | 1509 ms |
| Four-pane 2D pan frame | 4.4–5.0 ms |
| Four-pane 2D zoom frame | 6.0–7.2 ms |
| 3D orbit frame / draw | 4.5 / 0.7 ms |
| World drag preview frame / draw | 4.4 / 0.6 ms |
| Visible linked selection | 45 ms |
| World-edit persistence | 2679 ms |
| Projection + residual refresh after persistence | 1491 ms |
| Combined canonical edit + refresh | 4170 ms |
| Existing dense source-editor save + verification: before → after | 3389 → 6279 ms |
| 100-edit backend-only request profile | 1.707 s |

The source-editor save/readback result is a **regression**. It remains documented;
no speedup is claimed and no validation or fsync was bypassed. Source-editor pan/
zoom frame p95 is 16.3/22.6 ms versus baseline 10.7/13.5 ms. Draw p95 is 3.9/3.5 ms;
the lazy Three.js chunk is not loaded in this editor. Eight browser edit samples
do not isolate OS/cache variance. The backend-only profile and new multi-view
world-edit workload are different measurements, never substituted for this
comparison. Full original reports are retained.

First-request cProfile phases overlap and include instrumentation: schema
validation 3.001 s; semantic validation 0.286 s; revision hashing 0.086 s;
transaction commit 0.730 s; four fsync calls 0.008 s; snapshot 0.975 s. JSON self
time is 0.368 s. Nested cumulative serialization counts must not be summed.
Canonical validation and the 2.21 MB response are the profiled costs. The safe
changes avoid duplicate framework JSON conversion, share changed-file history
bytes and bound replay/history retention. Core safety checks remain active.

## 100-edit memory retention

RSS baseline **76.16 MiB**, sampled peak **149.99 MiB**, process high-water mark
**193.53 MiB**, after one second idle plus GC **142.06 MiB**. The sample series
plateaus during this finite window; this is not an unlimited-session leak claim.

Retained state: eight history edges / 32,006,371 unique bytes; three replay
responses / 6,634,231 serialized bytes; 5104 schema cache entries / 2,133,071 bytes.
Studio limits history to 100 edges / 32 MiB and replay to 128 entries / 8 MiB.
The core CLI keeps its unlimited default. Oversized history edges are not
retained; saves still commit. Old replay entries expire by LRU eviction; exact
revision fencing remains. Schema cache is 8192 entries / 8 MiB. Latest snapshots,
analyses, request objects and allocator memory are separate; no decoded images
are cached in the Python backend. Budgets are not total RSS bounds.

Reproduce: `python studio/backend/tests/profile_retention.py --label final --edits 100`.
See retention_100_edits.json. The separate three-edit installed v0.1B profile
identifies phase costs; its cold/short p95 is not a valid before/after speed claim.

## Tesla and Mark II

Tesla IoU SIDE **0.957230**, TOP **0.936083**, FRONT **0.931202**, REAR **0.944724**.
Fresh GLB positions/normals/indices/nodes match accepted output exactly; UV max
difference is 5.960464477539063e-08 (one float32 ULP). All eight proof images are
byte-identical; manifest, embedded GLB, Blender 53-cage/control check and both
viewer sizes pass. The cold seed copied no cached output/proofs. The existing
explicit accepted review remains valid against the actual proof/config hashes.

Mark II is unchanged, source **INCONSISTENT_SOURCE**, portability **BLOCKED**,
existing cage **FAIL**, surfaces/details **NOT STARTED**. Known greenhouse/pillar/
door conflicts appear over the primary calibrated reference; axle lock is 2730 mm.
The rejected rectification remains inactive; correction/scale diagnostics are
display only. See mark2_readonly.png and protected.json. No migration or repair.

## Definition of Done

- [x] Four-view workspace
- [x] Explicit observation/world distinction
- [x] Correspondence binding
- [x] Safe world-landmark edits
- [x] Multi-view XYZ proposal
- [x] No automatic proposal application
- [x] Per-view residuals
- [x] Individual critical failures
- [x] Heatmap
- [x] Consistency panel
- [x] Coverage display
- [x] Source review UI
- [x] Cage review UI
- [x] Source rejection blocks surfaces
- [x] Three.js cage preview
- [x] 2D/3D selection sync
- [x] Constrained 3D landmark move
- [x] Core-sampled curves
- [x] Axle/wheelbase diagnostic
- [x] SIDE/TOP ratio diagnostic
- [x] Rectification state
- [x] Canonical roundtrip
- [x] Undo/redo
- [x] Revision conflicts
- [x] E2E passes
- [x] Performance measured
- [x] Save latency profiled
- [x] Memory retention profiled
- [x] Tesla unchanged
- [x] Mark II untouched

## Reproduction and remaining limits

```powershell
python -m pip install -e ".[test]" -e "studio/backend[test]"
python -m pytest tests studio/backend/tests -q
cd studio/frontend
npm ci
npm test
npm run build
npm run e2e
```

Heavy gate: `python -m vehiclerecon run build/studio02-tesla-cold --no-cache`
from the repository root, with a private seed described above. CI keeps Blender
out of the four lightweight jobs; browser CI uses ANGLE/SwiftShader explicitly.

Canonical documents/reviews survive restart; live undo/leases/replay do not.
AUTO curves are explicitly approximate and mirrors display only. Vite warns
about the 589 kB lazy Three.js chunk; the source editor bundle remains separate.
CV/SAM/ONNX, Smart Edge, Magic Select, automatic wheels, full rectification/
surface editors, Blender Render and Cyberpunk adapter remain deferred.

Blockers: **none**. The save-latency regression is a recorded limitation, not an
unreported gate pass or a claim that either vehicle model is complete.
