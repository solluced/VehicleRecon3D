# VehicleRecon Studio v0.3 вЂ” measured release evidence

Runtime checkpoint: `394a9d648bc2df30a76ff9e53ba86c72fa33e26d`.
Base: `f152edd14802740ce27ff109cf4b8c6d3807856f`.
The [release report](release_report.json) contains all 32 Definition of Done
checks, exact runtime/tree identity, measurements, limitations and CI result.
Documentation/evidence commits after this runtime do not change production code.

| Gate | Evidence |
| --- | --- |
| 301 core/backend Python tests | [python.xml](python.xml) |
| 239 isolated core tests; 5 heavy tests deselected | [core_only.xml](core_only.xml), [optional packages absent](core_isolation.json) |
| 41 frontend tests | [frontend_tests.json](frontend_tests.json) |
| 13 real-browser flows | [browser_tests.json](browser_tests.json) |
| Smart Edge at DPR 2 / crop / zoom / pan; fit, ACCEPT, exact undo | Browser flow A/E; [screenshot](smart_edge.png) |
| Magic Select FG/BG, partial ACCEPT, immutable source bytes | Browser flow B; [screenshot](magic_select.png) |
| Circle candidates; explicit source-only acceptance | Browser flow C; [screenshot](wheels.png) |
| External change в†’ STALE and server 409 | Browser flow D; backend source/parameter/worker fencing tests |
| Disabled provider в†’ manual Point, Landmark, Measure | Browser flow F; preserved manual Polyline/Spline/restart flow |
| Registry/availability, edges, weak/noisy determinism, false positives, quality, fitting | `test_cv.py`, `test_contour_proposals.py` |
| Reject/edit no-op, source/cage review invalidation, exact undo | Backend CV/core byte-preservation tests |
| Cancellation, stale publication, failure, cache keys/budgets, no network | Backend controlled-provider and bounded-cache tests |
| UI mode/layer/inspector/roles/selection/mask/edge-map/stale | `cv-panel.test.tsx`; production Konva tested in the browser |
| Dense delta/ack equivalence and exact-schema-byte identity | `test_snapshot_delta.py`, `snapshot-delta.test.ts`, `test_compiled_schema_bundle.py` |
| 4K timings and actual visible proposal display | [cv_performance.json](cv_performance.json), [screenshot](cv_performance.png) |
| Analytic mask pixel IoU and contour/fit times | [cv_quality.json](cv_quality.json) |
| Dense save before/after and exact duplicated-work explanation | [save_comparison.json](save_comparison.json), [source editor](source_editor_performance.json) |
| в‰Ґ100 canonical edits with CV states/cache/eviction/RSS | [retention_100_edits.json](retention_100_edits.json) |
| Preserved multi-view / solver / reviews / Three.js / roundtrip | [multiview performance](multiview_performance.json), [roundtrip](roundtrip.json), [workspace](multiview.png), [gizmo](gizmo.png) |
| Independent installed wheels and seven exact static files | [packaging.json](packaging.json) |
| Two byte-identical frontend builds | [frontend_reproducibility.json](frontend_reproducibility.json) |
| Cold Tesla 14/14 and viewer desktop/mobile | [pipeline](tesla/pipeline_report.json), [delivery](tesla/delivery_report.json), [viewer](tesla/viewer_qa.json) |
| Frozen Tesla Blender control/topology and decoded GLB comparison | [control regression](tesla/control_regression.json), [glb_comparison.json](glb_comparison.json) |
| Protected Tesla/Mark II/frozen fixtures unchanged | [protected.json](protected.json), [read-only Mark II](mark2_readonly.png) |

Smart Edge preview p50/p95 is **742/2808 ms**, segment commit **464/843 ms** in
the finite 4K browser probe. The p95 includes a 2.808 s cold preview; subsequent samples are 0.487вЂ“0.754 s. Mask display/refinement takes seconds, without a
real-time claim. Native and browser brush probes use different stroke histories;
their timings are reported separately. Analytic mask IoU **1.0** is specific to
the synthetic fixture, not semantic vehicle recognition.

Dense source save plus verification p95 is **9442 ms**, versus **6279 ms** in
v0.2 and **3389 ms** in v0.1B. Response payload is **2,211,338 в†’ 175,847 bytes**.
This is a measured save regression against both prior versions. Schema/semantic/revision/transaction/fsync checks remain active. Profile phases
overlap; the first backend request is instrumented and is not a normal latency
sample. Eight browser saves do not isolate operating-system/cache variance.

The 100-edit mixed CV run reports RSS **83.4 в†’ 238.7 peak в†’ 173.4 MiB post-GC**.
It includes 10 accepts, 30 rejections, 60 stale proposals and one active result
at the end; the first rejected proposal is evicted. Data budgets remain bounded.
RSS also includes allocator/native/current-snapshot/request storage, and this
finite test does not prove leak freedom for every unlimited workload.

Offline browser tests block every off-origin request. On this Windows machine,
Kaspersky attempted one injected script request; it was blocked before network
transmission. Any other external attempt fails the test. Source-image egress is
zero. The local provider is also tested with external socket creation denied.

Tesla IoUs remain SIDE **0.957230**, TOP **0.936083**, FRONT **0.931202**, REAR
**0.944724**. GLB positions/normals/indices/nodes match exactly; UV difference is
at most one float32 ULP, and all eight presentation proof PNGs match byte-for-byte.
Mark II remains INCONSISTENT_SOURCE / portability BLOCKED / surfaces and details
NOT STARTED. No accepted geometry, source review or model was invented.

The only expected nonfailing tool warnings are the lazy Three.js chunk size
and Starlette TestClient/httpx deprecation. No neural models, ONNX, rectification
editor, surface editor, Blender Render button or Cyberpunk adapter is introduced.

`SHA256SUMS` identifies every evidence file except itself, after LF normalization.

Final runtime [CI run 39039204330](https://github.com/solluced/VehicleRecon3D/actions/runs/39039204330) is **4/4 PASS**; its
[real-browser artifact](ci_browser_tests.json) confirms **13/13 PASS** on Linux
with software WebGL. [Runtime equivalence](runtime_equivalence.json) identifies
the exact production blob list certified by these gates.
