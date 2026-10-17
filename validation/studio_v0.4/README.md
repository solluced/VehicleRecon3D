# VehicleRecon Studio v0.4 — release evidence

Runtime checkpoint: `21e66376810098314e718d0cbeb628ebba4fec6b`.
Base: `4ad04d0076aa28c72ae0a7ad396b9b56e0d714bd`.
The [release report](release_report.json) records all 31 Definition of Done gates.
[Runtime equivalence](runtime_equivalence.json) identifies the production blobs;
following documentation/evidence commits do not change them.

| Gate | Evidence |
| --- | --- |
| 320 local Python tests: 315 nonheavy + 5 Blender/integration | [test matrix](tests.json) |
| 254 isolated core tests; optional Studio/CV dependencies absent | [isolation](core_isolation.json) |
| 48 frontend tests | [raw results](frontend_tests.json) |
| 17 complete browser flows, zero failures/skips/flaky cases | [raw results](browser_tests.json) |
| Manual anchor dragging, FIT/HELD_OUT roles, two-candidate comparison | Browser positive flow; [screenshot](positive_fixture.png) |
| Positive activation, review invalidation, independent source review, exact undo | [positive fixture](positive_fixture.json), core/API tests, browser positive flow |
| Exact scale boundary: inside/exact eligible, outside ineligible | [candidate results](borderline_fixture.json), `test_exact_scale_boundary_and_analytic_extrema` |
| Invalid knots/domains/scale/locks/evidence/extrapolation, individual held-out failure | Core reconciliation tests and API activation fences |
| Stale calibration/source/crop, rejected historical evidence and reason | Core/API/frontend tests; browser stale flow |
| Real decoded RAW/RECTIFIED PNGs; parallel preview requests | Reconciliation API concurrency test and browser image decode checks |
| Read-only Mark II rejection and protected hashes | [audit](mark2.json), [screenshot](mark2_rejected.png), [hashes](protected.json) |
| Source replacement without measured/world transfer; exact undo | [asserted behavior](source_replacement.json), browser/API tests |
| Source-save call counts/times, transaction writes and API response render | [100-edit profile](retention_100_edits.json), [comparison](save_comparison.json) |
| Calibrated dense edit and actual residual refresh | [separate profile](calibrated_edit_profile.json) |
| Smart Edge decode/cache/path/serialization equivalence and timings | [native profile](smart_edge_native_profile.json) |
| Debounce/HTTP/poll/React/Konva phases and current Magic Select timing | [browser CV timing](cv_performance.json), [screenshot](cv_performance.png) |
| 100 canonical edits + 100 candidate create/reject cycles, CV caches/history/RSS | [retention](retention_100_edits.json) |
| Preserved four-view, 3D, solver, reviews, gizmos and roundtrip | Browser flows; [performance](multiview_performance.json), [screenshot](multiview_performance.png) |
| Two byte-identical final frontend builds | [reproducibility](frontend_reproducibility.json) |
| Independently installed wheels and nine exact static files | [packaging](packaging.json) |
| Fresh Tesla 14/14; frozen control points and topology | [pipeline](tesla/pipeline_report.json), [control regression](tesla/control_regression.json) |
| Tesla decoded GLB and desktop/mobile viewers | [GLB comparison](glb_comparison.json), [viewer QA](tesla/viewer_qa.json), [delivery](tesla/delivery_report.json) |
| Four CI jobs on the exact runtime checkpoint | [CI result](ci.json), [GitHub run](https://github.com/solluced/VehicleRecon3D/actions/runs/39054822368) |

Final source-editor save plus canonical verification p95 is **2340 ms**, versus
v0.1B **3389**, v0.2 **6279**, v0.3 **9442 ms**, with the same 4K/5000/20-layer
scenario. The earlier 2320/2738 ms checkpoints are not substituted for the final
frozen-build measurement. Profile phases overlap and differ from uninstrumented
browser latency. [Development notes](../../docs/studio_development.md) explain
the exact-schema, positive-document memo, full audit equivalence and revision-fenced
reuse of the just-committed workspace. No cross-document semantic check is skipped.

The source-only mutation performs 2 Workspace loads / 21 schema / 4 semantic /
11 revision / 1 snapshot / 4 atomic writes / 4 fsync calls. Its fixture has no
calibrated residuals. The separate calibrated 5000-entity case has 68 bound rows:
2 residual computations during mutation and 4 during explicit analysis. Current
source-only delta is about 175847 bytes; after ten additional accepted CV curves
the retention run's final delta is 208702 bytes. Calibrated world-edit delta /
analysis responses are 69454 / 175441 bytes.

The positive fixture's maximum correction is **1.889 px / 37.776 mm equivalent
source correction**, local scale **0.921516–1.075092**, held-out RMS **1.153 →
approximately zero px**, failed critical count **5 → 0**. Metric equivalents
describe an affine image-domain correction, not a physical geometry change.

Mark II remains **REJECTED / NOT ACTIVE / OUTSIDE SCALE LIMIT**. Its between-axle
maximum is **42.037 px / 244.170 mm equivalent**, whole-crop maximum **236.902 px /
1376.051 mm equivalent**, RMS **73.163 px**, scale **0.518262–2.150012**. Source is
INCONSISTENT_SOURCE, portability BLOCKED, cage FAIL, surfaces/details NOT STARTED.
All nine protected hashes and all protected tracked project/fixture paths remain
unchanged. No geometry or source acceptance was invented.

Smart Edge browser p50/p95 changes **742/2808 → 242/291 ms**; previous warm
samples were 487–754 ms. Native identical-segment warm p50 changes **69.6 →
21.8 ms**, with exact structured result equivalence. Debounce stays 80 ms and
polling 20 ms. Raw browser phase/resource samples are retained; residual transport/
validation/poll overhead is not mislabelled as isolated network time. Magic Select
remains a seconds-scale CPU method, without a realtime or semantic recognition claim.

The mixed 100-edit + 100-candidate run reports RSS **88.1 → 355.3 process peak →
310.2 MiB post-GC**, plateauing around 310–311 MiB after edit 70. It retains 30.75
MiB undo data, 7.89 MiB replay data, 42.12 MiB CV fields, 1.37/0.66 MiB proposals/
results, 1.23 MiB candidate reports, 39.2 KiB preview PNGs and 14.32 MiB whole-document
memo data, all within explicit byte/count limits. The 100-record archive occupies
213.7 KiB on disk. Budgets count payloads separately from process/native/allocator
RSS; this finite run does not prove unlimited leak freedom or isolate all causes
of its higher RSS than the v0.3 workload without rectification previews.

All reconciliation flows work with CV disabled. Replacement images are imported
through the ordinary authenticated project-scoped PNG/JPEG path. Original bytes
and observations remain retained; normalized landmark transfer is a proposal only.
The replacement's framing requires explicit core recalibration; v0.4 introduces no
new calibration solver. ONNX remains optional and unimplemented. Surface/topology
authoring, Blender Render orchestration and final export/Cyberpunk workflows remain
deferred. The existing lazy Three.js chunk warning and TestClient/httpx deprecation
are nonfailing tool warnings.

`SHA256SUMS` covers every evidence file except itself after LF normalization.
