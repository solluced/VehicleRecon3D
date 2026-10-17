# Studio development — v0.1B

Studio is a separate optional Python distribution and React/TypeScript/Konva
workspace. Mandatory core dependencies remain unchanged. Human release name is
v0.1B; the optional distribution/frontend package version is 0.1.1. Canonical
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
| POST `/projects/{id}/transactions` | Allowlisted typed manual-source commands |
| POST `/projects/{id}/undo`, `/redo`, `/reload` | Core live-session history and explicit resync |
| POST `/projects/{id}/reference-imports` | Bounded original-byte import and core registration |
| GET `/projects/{id}/references/{ref}/image` | Registered hash-verified original bytes |
| POST `/projects/{id}/preferences` | Typed UI-only `.studio/session.json` |
| GET `/events?tab_id=...` | One bounded, replayable SSE channel per tab |

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
The phase evidence and commands are in `validation/studio_v0.1b/`. CI definitions
do not by themselves claim that remote jobs or the heavy release gate passed.

Primary API references: [FastAPI responses](https://fastapi.tiangolo.com/advanced/custom-response/),
[Konva performance](https://konvajs.org/docs/performance/All_Performance_Tips.html),
[Vite](https://vite.dev/guide/), [Playwright](https://playwright.dev/docs/test-webserver),
[jsonschema extension](https://python-jsonschema.readthedocs.io/en/stable/creating/).
