# VehicleRecon Studio v0.5 — release evidence

Status: **PASS**, all 34 Definition of Done items satisfied within the trusted core
capabilities documented below. Runtime: `a3fd25e293157f157fa13307707fa85fc82535c0`; baseline: `354671dee26b0817f48b2ace625b08160e0bbf0f`.
[CI: four jobs PASS](https://github.com/solluced/VehicleRecon3D/actions/runs/39059086712).
The final documentation/evidence commit preserves the certified production tree;
`runtime_identity.json` records its exact Git blobs.

The Surfaces workspace reuses canonical `generated/surface_graph.json`. Its registry
contains 13 trusted operations, with 12 point/curve/surface operations
evaluable for coarse feedback. Surface previews support Coons, cubic boundary roll,
arch annulus, ribbon, bilinear patch and curve-derived lerp. Discrete boundary stitch
preview is disabled. No expressions, scripting or second surface engine is added.

Stable patch/node IDs, typed atomic commands, safe incomplete drafts, boundary
picking/orientation, exact undo/redo, material roles, supported mirror/sampling rows,
dependency selection, revision-bound preview, real mesh wireframe and normals are
covered by core/API/browser tests. G0 uses individual max/RMS gaps and tolerance;
normal-angle compatibility is labelled G1-like, without strict G1/G2 claims.

## Observed gates

| Check | Result |
|---|---|
| Python, including five heavy tests | 344 PASS |
| Frontend unit tests | 51 PASS |
| Full browser suite | 24 PASS |
| Final surface browser recheck | 7 PASS |
| Separate 100-edit browser retention gate | 1 PASS |
| GitHub CI | core/backend/frontend/browser 4/4 PASS |
| Installed wheels | schema/registry/assets/bootstrap and core isolation PASS |
| Positive synthetic fixture | two adjacent patches; evaluation/G0/topology PASS |
| Negative preview evidence | eight cases correctly FAIL; further gates in tests |
| Protected project/fixture paths | unchanged versus baseline |

## Measured performance and retention

Windows / Edge / Ryzen 7 5800X, 1500×1000, DPR 1. Source-save benchmark code,
4K source, 5000 entities and 20 display layers are unchanged from v0.4.

| Metric | Observed value |
|---|---|
| v0.4 dense source visible save + readback p95 | 2340 ms |
| v0.5 same source save p95 | 2342 ms |
| Surface parameter edit p50 / p95 | 192.5 / 227.3 ms |
| First core medium preview, 27 patches | 1138.1 ms |
| Incremental core preview p50 / p95 | 303.3 / 381.6 ms |
| Draft patch creation | 181.3 ms |
| Browser patch resolution edit + visible stale/readback, one sample | 850.0 ms |
| First / incremental visible browser preview, low | 836.7 / 327.3 ms |
| Three.js upload / redraw | 23.9 / 15.4 ms |
| Selection / wire / normals toggle | 3.8 / 51.3 / 30.1 ms |
| 100 surface edits + real CV caches, RSS baseline / peak / post-GC | 44.7 / 181.5 / 175.7 MiB |
| 100 real UI edits, heap baseline / peak / post-GC | 7.4 / 23.0 / 10.1 MiB |
| Preview / history serialized payload | 1729569 / 2407453 bytes |

These are distinct workloads. Core retention includes 100 medium-resolution edits,
the 27-patch mixed Coons/bilinear graph, actual CV fields/results, mesh cache and
bounded history. Browser retention performs 100 real parameter commits and preview
updates; its backend RSS is sampled alongside browser GC, while explicit Python GC
is measured in the separate core/CV workload. Neither is compared as if it were the
v0.4 dense-source/CV retention workload. Per-edit samples and byte budgets are in
the JSON reports. Incremental evaluation samples only the changed patch/downstream
dependencies; unchanged meshes are reused, with current gates always rechecked.

## Preserved vehicles and explicit limitations

Fresh cold Tesla: SIDE **0.957230**, TOP **0.936083**, FRONT **0.931202**,
REAR **0.944724**; **14/14 PASS**, geometry, direct GLB and desktop/mobile viewers PASS.
Frozen Blender control comparison passes. GLB positions, normals, indices and nodes
match the accepted asset; UV maximum difference is one float32 ULP. All eight visual
proofs match byte-for-byte. Accepted geometry was not edited.

Mark II's nine protected hashes remain unchanged. Source INCONSISTENT_SOURCE,
portability BLOCKED, cage FAIL, surfaces/details NOT STARTED. A private read-only
Mark II browser copy verifies Surfaces is blocked with no override or canonical write.

The trusted core has no arbitrary previous-patch edge extraction operation. AUTO
handles and non-monotone-X cage boundaries are not offered as executable coarse
boundaries. Support rows expose actual sampling positions, without invented strength
or offset semantics; mirror is the existing Y=0 contract. Self-intersection audit
remains Blender-owned. These are capability-disabled limits, not hidden approximations.
Preview is explicitly **COARSE AUTHORING PREVIEW / preview topology**, with no final
Class-A, strict G1/G2, export or game-readiness certification. Render orchestration,
final export UI and Cyberpunk remain deferred. Release blockers: **none**.

See [the full DoD report](release_report.json), [surface contracts](../../docs/surface_authoring.md)
and [the user manual](../../docs/studio_user_manual_v0.5.md).
