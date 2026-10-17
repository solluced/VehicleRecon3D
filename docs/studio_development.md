# Studio development — v0.2

Studio is a separate optional Python distribution and React/TypeScript/Konva/Three.js
workspace. Mandatory core dependencies remain unchanged. Human release name is
v0.2; the optional distribution/frontend package version is 0.2.0. Canonical
document version 2 and transport `/api/v1` are independent versions.

## Install and run

Core only, without FastAPI, Pillow, Uvicorn or Node:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python -m vehiclerecon inspect projects/tesla
```

Add the optional Studio distribution:

```powershell
python -m pip install -e "studio/backend[test]"
vehicle-recon studio --root F:/T/projects
# Equivalent:
python -m vehiclerecon studio --root F:/T/projects
```

The checked-in production frontend is included in the Studio wheel. Normal
launch needs no Node process or Blender. The default allowed root is
`<working-directory>/projects`; explicit roots must already exist. Repeat `--root`
for additional trusted roots. Only immediate child project directories are
indexed. A browser cannot supply filesystem roots. Normal launch opens the
default browser with a one-time bootstrap fragment, prints only the nonsensitive
base URL, and chooses a free `127.0.0.1` port. `--port` can select a local port;
other hosts are refused. Ctrl+C stops the server and closes active SSE streams.
`--no-browser` is a diagnostic/embedding option; it deliberately does not print
authentication secrets. Use normal launch for the interactive session.

Frontend developer build, tested with Node 24 and Python 3.12:

```powershell
cd studio/frontend
npm ci
npm run build
npm test
npm run e2e
```

The lockfile pins packages. `build` generates canonical TS contracts, type-checks
and writes bundled assets into `studio/backend/src/vehiclerecon_studio/static`.
`npm run dev` rebuilds those same-origin assets in watch mode; keep the normal
backend running and refresh the browser. No cross-origin development proxy or
permissive CORS exception is needed. `studio/shared/generate_types.py` reads only
local canonical schemas; generated renderer-independent types are not another
geometry format. Restart Studio after changing trusted core code/schemas/profiles.

Build release wheels from a clean checkout or a fresh build directory. Setuptools
can retain removed assets in an old `studio/backend/build/lib` directory; a wheel
must contain exactly the current `static/index.html` and its four asset files,
including both lazy chunks. The v0.2 installed-wheel check verifies every asset
against the current source bytes and checks the packaged solver schema.

## Implemented adapters

`security.py` enforces exact Host/Origin, same-origin fetch metadata, session and
CSRF protection, content types, request budgets and response headers. Bootstrap
expires after five minutes and is single-use. Sessions use HttpOnly host-only
SameSite=Strict cookies with a twelve-hour lifetime. API reads, schemas, original
images and events require authentication. OpenAPI/docs HTTP routes are disabled.
Static boot assets alone are public. No tokens appear in resource/event URLs.

The CSP permits only self scripts/styles/connections, self/blob images, and no
objects, base URLs or framing. `style-src-attr 'unsafe-inline'` is limited to
style attributes needed for Konva's numeric canvas/layout sizing; script sources
and style elements receive no unsafe-inline/eval exception. Assets/fonts are
local. There is no telemetry, CV runtime, model download or remote inference.

`workspace.Registry` resolves opaque IDs under startup roots and rejects path
traversal, symlinks/junctions and unsafe creation names/case aliases. Imports
decode only PNG/JPEG under 64 MiB encoded, 64 megapixels decoded, two concurrent
decodes and a 512 MiB project input budget. Original bytes are preserved under
SHA256-derived filenames. EXIF-rotated imports are rejected with an upright-source
message, rather than silently changing the decoded authoring frame or source.

Each writable project has one expiring tab/session editor lease. Commands and
history use `AuthoringSession`, revisions, `ProjectLock`, the existing journalled
transaction service and core schema/semantic validation. All canonical mutations
require matching `expected_revision`/If-Match, CSRF and an idempotency key. Project
creation uses the allowed root's revision; lease/bootstrap operations have their
own preconditions. Backend coordination serializes its own readers/writers;
external CLI locks still return 423. No route accepts paths to writable files,
shell commands, executables, geometry scripts or arbitrary JSON patches.

| Actual operation | Adapter |
| --- | --- |
| POST `/session/bootstrap`, GET `/session` | One-time launch exchange / current session |
| GET `/roots`, `/projects`, `/capabilities`, `/schemas` | Allowed registry, versions and canonical contracts |
| POST `/projects` | Safe v2 DRAFT creation through core |
| GET `/projects/{id}`, `/revision`, `/readiness`, `/observations` | Current canonical snapshot and derived core feedback |
| POST `/projects/{id}/leases`, `/release` | Acquire/renew/release own editor lease |
| POST `/projects/{id}/transactions` | Allowlisted typed source/world/correspondence commands |
| POST `/projects/{id}/undo`, `/redo`, `/reload` | Core live-session history and explicit resync |
| POST `/projects/{id}/reference-imports` | Bounded original-byte import and core registration |
| GET `/projects/{id}/references/{ref}/image` | Registered hash-verified original bytes |
| POST `/projects/{id}/preferences` | Typed UI-only `.studio/session.json` |
| GET `/events?tab_id=...` | One bounded, replayable SSE channel per tab |
| GET `/projects/{id}/analysis` | Revision-bound residuals, coverage, reviews and automotive diagnostics |
| GET `/projects/{id}/residuals`, `/cage-preview`, `/correspondences`, `/world-landmarks` | Project-scoped typed read models |
| POST `/projects/{id}/fit-proposals` | Typed fit/plane placement, no canonical write |
| POST `/projects/{id}/apply-fit` | Server-retained proposal, fenced to project/tab/revision, one core command |
| POST `/projects/{id}/source-review`, `/cage-review` | Explicit inspected-subject reviews through core |

Paths are relative to `/api/v1`. This subset supersedes illustrative route names
only where necessary; the rest of the locked backend API remains planned.
V1 opens read-only. Migration is deliberately an explicit core CLI operation on
a copy, outside this editor. No automatic migration or review acceptance exists.

## Revisions and performance boundaries

SSE events are hints. The client ignores its own delayed notifications and
rechecks canonical revisions before reporting external conflict. An epoch/expired
cursor produces resync. A replaced connection reconnects with Last-Event-ID.
Lease renewals and presentation saves cannot overwrite a newer canonical
snapshot or interrupt an otherwise valid drag. In-progress gestures are local;
one typed command persists at drag end. Failed commits restore canonical drawing.

Read-only snapshots are cached by exact authoring revision and independent
required/stored review-proof hashes. UI state and history flags are read afresh.
The cache is disposable; canonical files remain authoritative. Core readiness
can reuse a current validated Workspace, retaining its revision check.

The dense workload exposed repeated structural validation. The generic core
optimization dispatches oneOf only when unique required string consts make every
other branch impossible. A bounded cache (8192 entries / 8 MiB serialized data)
memoizes only successful structural results against exact record content, union
schema and all referenced schemas. Semantic source/crop/ID/profile/binding checks
and reviews always rerun. Tests compare valid/invalid results to the unmodified
Draft 2020-12 validator and test schema/data cache invalidation. No profile floor
or review gate is relaxed.

Konva owns two physical canvas layers: a static source and batched vector groups.
The UI's logical display layers remain independently visible/locked/transparent.
A spatial index picks controls; native paths pick source-curve strokes. Canonical
points/Bezier handles are the source data, never Konva serialization. Profiling
attributes expose current viewport, pick and redraw timing for browser tests.

## Validation and CI

```powershell
python -m pytest tests studio/backend/tests -q
cd studio/frontend
npm test
npm run e2e
```

Browser tests use temporary copies and a private stdin bootstrap harness; they
never edit committed fixtures or Mark II. Tests cover complete manual roundtrip,
browser refresh, backend restart, SSE replacement/reconnect, external conflict,
desktop/laptop with DPR 2, and a 3840×2160 image with 5000 canonical controls and
20 logical layers. Performance reports include actual frame/picking/commit
latencies, post-GC JS heap and backend RSS measurements, not assumed compliance.
Memory samples span eight real edits with live undo history and idempotency
responses retained; they are not a long-session leak certification. Local drag
preview timing is measured separately from canonical persistence/readback.

`.github/workflows/studio.yml` separates core-only Python, optional backend,
frontend build/unit and real Chromium E2E jobs. Lightweight jobs do not require
Blender. The full cold fourteen-stage Tesla/GLB/desktop/mobile regression remains
a required release gate, run locally with Blender and the existing browser QA.
The phase evidence and commands are in `validation/studio_v0.2/`. CI definitions
do not by themselves claim that remote jobs or the heavy release gate passed.

Primary API references: [FastAPI responses](https://fastapi.tiangolo.com/advanced/custom-response/),
[Konva performance](https://konvajs.org/docs/performance/All_Performance_Tips.html),
[Vite](https://vite.dev/guide/), [Playwright](https://playwright.dev/docs/test-webserver),
[jsonschema extension](https://python-jsonschema.readthedocs.io/en/stable/creating/).

## v0.2 multi-view / Three.js boundaries

`MultiWorkspace` reuses the existing SourceCanvas and Properties adapters. Each
pane has an independent viewport/crop and uses the exact calibrated source hash.
The source editor, multi-view UI and Three.js renderer are separate lazy chunks;
opening the source editor does not load Three.js. No model/URL/file loader or
arbitrary compute route is introduced. Three.js consumes core scene/sample DTOs,
owns camera/ray picking/gizmos only, and disposes geometry, materials, controls,
observers, renderer and WebGL context when unmounted.

`authoring.fitting` implements deterministic constrained proposals using existing
CalibrationTransform projection. [Math and conditioning](multiview_fitting.md)
document the objective, uncertainty/weights, exclusions and exact constraints.
The typed `landmark_fit` schema is a core resource. The backend retains at most
32 proposals for 300 seconds, scoped to project, authenticated tab and exact
revision. Apply reads the server-retained XYZ and calls one typed core command.
Clients cannot substitute arbitrary proposal coordinates. Stale proposals are
rejected; browser conflicts clear ghosts. Reviews likewise require the inspected
subject plus current revision and go through existing core review services.

Core analysis supplies individual residuals, a declared relative-tolerance heat
policy, semantic/stable-point coverage, axle/wheelbase and SIDE/TOP ratios.
Unavailable/unregistered evidence is UNKNOWN/BLOCKED, not an invented projection.
Legacy diagnostics consume recognized project-scoped report contracts, verify
input/calibration/cage hashes and never migrate or rewrite the project. Mark II
is a read-only regression case, never a geometry branch in the solver.

The existing SSE channel adds `residuals_changed`, `source_review_changed` and
`cage_review_changed` notifications. Pointer motion stays local. Events remain
hints; exact revision/subject checks govern writes and derived evidence.

## Dense save and memory retention

All validation, revision hashing, journal recovery and fsync remain active.
Mutation endpoints return validated JSONResponse objects directly, avoiding a
second FastAPI recursive conversion of large already-JSON-safe snapshots.
Transport equivalence, Unicode, canonical state and idempotent replay are tested.
Cold schema validation and full snapshot payloads remain costs; performance is
reported separately from local gesture frames rather than hidden in FPS claims.

Core history now stores changed-file before/after edges and shares exact
immutable bytes between adjacent edges. Its default limits remain unlimited for
CLI compatibility. Studio explicitly chooses at most 100 edges / 32 MiB unique
document bytes per live session, pruning oldest edges. A single edge larger than
the byte budget is not retained; saving is still transactional. History flags
reflect actual available undo. New edits clear redo, exactly as before.

Idempotency responses use an LRU of at most 128 entries / 8 MiB serialized bytes.
Old entries are evicted; an oversized result is not cached. Replays of retained
keys return the same response, and altered requests conflict. Revision fencing
still protects an expired/evicted canonical retry. This cache and live undo do
not survive restart. UI preferences are best effort. Schema memoization remains
8192 entries / 8 MiB, keyed to exact records and schemas. One latest snapshot and
one derived analysis are cached per opened project; no decoded images are cached
by the backend. Browser/GPU image storage is separate from Python RSS.

Reproduce a 100-edit backend profile:

```powershell
python studio/backend/tests/profile_retention.py --label final --edits 100
```

The probe creates an ignored private fixture, uses authenticated typed API
transactions, records baseline/process peak/idle-GC RSS, retained history/replay/
schema bytes, payload size and first-request cProfile phases. Profiling times
overlap and include instrumentation; later per-edit samples are unprofiled.
`--package-root` can select an independently installed baseline wheel tree.
Compare like-for-like source-editor browser measurements separately from the
new four-view/3D world-edit workload. Measurements do not certify leak freedom
for unlimited projects/tabs or all hardware.

The final local v0.2 matrix records source-editor save plus verification p95
**6279 ms**, compared with the committed v0.1B **3389 ms** on the same nominal
5000-point workload. This is a measured regression, not an improvement claim.
The separate four-view/3D workload records persistence **2679 ms**, subsequent
projection/residual refresh **1491 ms**, total **4170 ms** p95. Eight samples per
browser workload do not isolate OS/cache variance. The 100-edit authenticated
backend-only profile records p95 **1.707 s** without browser/readback. Its first,
instrumented request attributes overlapping cumulative time to schema validation
(3.001 s), semantic validation (0.286 s), revision hashing (0.086 s), transaction
commit (0.730 s, including 0.008 s in four fsync calls), and snapshot refresh
(0.975 s). JSON serialization self time is 0.368 s; its nested cumulative counts
must not be summed. Full canonical validation and the 2.21 MB response remain
the principal profiled costs. No validation or durability check was removed.

Across 100 edits RSS is 76.16 MiB baseline, 149.99 MiB sampled peak, 193.53 MiB
process high-water mark and 142.06 MiB after one second idle plus GC. Retention
is eight undo edges / 32,006,371 unique bytes, three replay responses / 6,634,231
serialized bytes, and 5104 schema entries / 2,133,071 bytes. Samples plateau in
this finite window; allocator/request/latest-snapshot memory remains outside
those byte budgets. This identifies bounded retained state without claiming
that every possible long-running workload is leak-free. Release evidence keeps
the complete samples, profiles, environment and browser reports.

CI still has four separate jobs; new core tests use NumPy only, and Three.js
behavior lives in frontend/browser jobs. GPU-less CI explicitly chooses
ANGLE/SwiftShader driver mode through `VEHICLERECON_SOFTWARE_GL=1`; local runs
keep the browser's default renderer. See Chromium's
[driver-mode switches](https://chromium.googlesource.com/chromium/src/+/main/docs/gpu/swiftshader.md).
Real 3D gizmo tests verify locked coordinates and exactly one command on release.
The heavy cold Tesla/Blender regression stays a separate release gate.
