# Studio local backend contract

Status: **proposed API v1, not implemented**. Document-schema versions are
independent. FastAPI/OpenAPI and generated TypeScript clients are planned;
the examples below are contract prototypes, not existing endpoints.

## Startup and transport

Future command: `vehicle-recon studio`, optionally with trusted startup
configuration selecting allowed project roots and a Blender executable. Bind
`127.0.0.1` on an available port, serve the built frontend and `/api/v1` on that
same origin, and open a browser with a one-time bootstrap fragment. Headless
commands must not import Studio or require its dependencies.

Use JSON REST for requests, binary responses for registered images/GLBs, and one
SSE event stream per tab. A random launch secret establishes an authenticated
same-origin session; see [security](studio_security.md). WebSocket transport is
not needed initially. Preview requests are coalesced at <=20 Hz with stale
sequence suppression; SSE carries notifications, not pointer-coordinate streams.

The backend owns project indexing, schema access, canonical transactions,
reference/artifact serving, preview/validation services, job dispatch, logs,
watching and locks. Core owns geometry, calibration math, checks, stage/cache
semantics and review validation. No route accepts a shell command, executable,
module name, arbitrary filesystem path or executable project expression.

## Common request/response rules

Project/root/reference/artifact/job/schema IDs are opaque registry IDs. Resolve
them to allowlisted objects internally. A document kind is one of `project`,
`calibration`, `cage`, `surface_graph`, `details`, `silhouette_traces`; its actual
path comes from validated project metadata. No caller-supplied file path endpoint
exists. Generated TS declarations mirror canonical schemas and this API; they
are never a separately maintained geometry schema.

Authenticated reads return document/project revision, schema IDs/versions,
capabilities and read-only/readiness information. Send ETag for exact document
bytes; project revision is the content-derived aggregate in
[data flow](studio_data_flow.md#revisioned-save-and-crash-consistency). Mutations
require CSRF protection, `If-Match` project revision, an active editor lease and
`Idempotency-Key`. Retries with the same key and payload return the same result;
a different payload with that key returns 409. A new server epoch reports
whether the bounded idempotency journal still contains the prior result.

| HTTP code | Contract |
|---|---|
| 200 / 201 | Read/current committed resource or newly created record |
| 202 | Accepted job/diagnostic request; not a validation PASS |
| 400 | Malformed request or unknown operation |
| 401 / 403 | Missing session, origin/CSRF/permission rejection |
| 404 | Opaque object unavailable within this session's registered roots |
| 409 | Revision, binding, migration, active-run or idempotency conflict |
| 410 | Event/log cursor or disposable proposal no longer retained |
| 413 | Upload, geometry, request or decoded-image budget exceeded |
| 422 | Schema/semantic/gate rejection with structured field issues |
| 423 | Conflicting project lock or write lease |
| 428 | Required revision/precondition missing |
| 500 | Internal fault with diagnostic ID; no stack/path/secret exposure |

Error bodies contain `code`, `message`, `issues[]` (document/entity/pointer),
`retryable`, `current_revision` where safe and a diagnostic ID. Error codes such
as `STALE_REVISION`, `UNSUPPORTED_SCHEMA`, `IMMUTABLE_DATUM`,
`REFERENCE_INCONSISTENT` and `VISUAL_REVIEW_STALE` are machine-readable causes,
not new pipeline result statuses.

## Proposed operations

All paths below are relative to `/api/v1`. Every mutable operation shares the
revision/validation/locking service, including specialized routes.

| Method and path | Responsibility / constraints |
|---|---|
| `POST /session/bootstrap` | Exchange one-time launch secret for session cookie and CSRF token; exact Origin/Host checks |
| `GET /capabilities` | Supported API/document versions, core operations, providers, feature gates and runtime availability |
| `GET /roots` | Display registered roots as opaque IDs; no directory traversal |
| `GET /projects` | Indexed projects with identity, readiness, source disposition and last results |
| `POST /projects` | Create under a configured writable root with name/profile; no existing-file overwrite or invented dimensions |
| `GET /projects/{p}` | Metadata, current revision, document inventory, locks and readiness |
| `GET /schemas` / `GET /schemas/{s}` | Exact canonical schema/profile inventory and UI metadata; no remote arbitrary `$ref` loading |
| `GET /projects/{p}/documents/{kind}` | Canonical JSON with schema/version/hash; metadata is `kind=project` |
| `POST /projects/{p}/transactions` | Apply typed multi-document authoring commands; sole canonical write primitive |
| `GET /projects/{p}/references` | Registered role/source/crop/hash/size inventory |
| `POST /projects/{p}/reference-imports` | Import upload as immutable source; resource quotas and decoder checks; role assignment through a transaction |
| `GET /projects/{p}/references/{r}/image` | Original bytes or explicit derived display rendition with separate identity |
| `GET /projects/{p}/observations` | Typed source observations/source curves and shared bindings; canonical storage is calibration |
| `POST /projects/{p}/previews` | Validate draft command set and return core-derived sampled cage/projections/coarse patch feedback, without canonical writes |
| `POST /projects/{p}/diagnostics` | Schema, calibration, correspondence, source consistency or bounded graph checks for the asserted revision |
| `GET /projects/{p}/validation` | Registered reports with current/historical/freshness bindings; no invented results |
| `GET /projects/{p}/rectification-candidates` | Inactive/accepted/rejected candidate inventory |
| `POST /projects/{p}/rectification-candidates` | Save structurally valid candidate record and trusted-fit/held-out provenance; numerical rejection may still be recorded |
| `POST /projects/{p}/rectification-candidates/{c}/diagnostics` | Core interpolation, monotonicity, scale/magnitude and held-out checks without activation |
| `POST /projects/{p}/rectification-candidates/{c}/decisions` | Explicit accept/reject with current diagnostic subject hash; accept activates via transaction only if allowed |
| `POST /projects/{p}/reference-reviews` | Proposed generic ACCEPTED / NEEDS_CORRECTION / INCONSISTENT_SOURCE decision with reason and evidence hashes |
| `POST /projects/{p}/cage-reviews` | Proposed generic explicit cage review; binds all critical coverage/results |
| `POST /projects/{p}/review` | Existing final core review: reviewer, PASS/FAIL, note(s), limitation(s), current proof/geometry/input hashes |
| `POST /projects/{p}/leases` | Acquire one editor lease; other tabs inspect read-only |
| `POST /projects/{p}/leases/{l}/renew` / `DELETE .../{l}` | Renew/release own lease; cannot steal another writer/build lock |
| `POST /projects/{p}/checkpoints` | Named canonical snapshot + manifest, no Git commit |
| `GET /projects/{p}/checkpoints` | Enumerate safe checkpoint IDs and subject revisions |
| `POST /projects/{p}/checkpoint-restores` | Validated restore as a new transaction after diff; old artifact reviews not promoted |
| `POST /projects/{p}/migrations/preview` | Supported version-pair dry-run, diff, readiness/regression implications |
| `POST /projects/{p}/migrations` | Explicit backed-up migration transaction; no implicit save upgrade |
| `POST /projects/{p}/runs` | Queue allowlisted core pipeline request with pinned input revision |
| `GET /runs/{j}` | Job activity, exact native results, active stage, input identities and process lifecycle |
| `POST /runs/{j}/cancel` | Request managed cancellation; no arbitrary process ID |
| `GET /runs/{j}/logs` | Bounded stdout/stderr by cursor/channel; opaque job ID, escaped text |
| `GET /projects/{p}/artifacts` / `GET /artifacts/{a}` | Manifest-registered, hash-bound proofs/GLB/viewer; no path argument |
| `GET /events` | Authenticated multiplexed SSE stream for this tab's authorized subscriptions |

Calibration, cage, graph and details are exposed as document kinds plus typed
transactions; separate raw file-write routes are deliberately unnecessary.
Specialized endpoints translate to these same headless services. Raw property
forms may submit only schema-supported, allowlisted paths for their document
kind, not executable JSON Patch paths into arbitrary files.

## Transaction and preview prototypes

Synthetic command example, requiring the future generic authoring contract:

```json
{
  "base_revision": "sha256:<project-revision>",
  "lease_id": "lease-opaque",
  "commands": [{
    "id": "command-opaque",
    "type": "MoveObservation",
    "target": {"view": "side", "observation_id": "obs-side-a-roof-left"},
    "expected_pixel": [500, 200],
    "pixel": [502, 201],
    "reason": "Correct visible roof/window corner"
  }]
}
```

Response includes new project/document hashes, normalized committed command(s),
inverse/recovery references, readiness issues and a dependency-based staleness
estimate. Returning success means schema/semantic validation and the complete
transaction committed, not that the car passes validation. Source hash, profile
floor, locked datum, acceptance/review fields and derived report hashes cannot be
arbitrarily set by a property form. Specialized review/import/migration services
validate those fields from actual evidence.

`MoveWorldLandmark`, `AddSplinePoint`, `SplitCurve`, `MergeCurves`,
`DeleteLandmark`, `SetConstraint`, `ChangeSemanticRole`, `SetTolerance` and
`SetCalibration` have separate typed request schemas. An explicit world move
specifies canonical point/instance, target XYZ or supported movement constraint,
and expected old value. A single-view 2D drag with unresolved depth returns a
constraint issue; it cannot default to a new world point in that view.

Preview requests carry base revision, local draft sequence and a bounded command
set. The backend validates in memory and invokes core services, then returns
that same revision/sequence, sampled geometry, all-view projection/residual rows,
warnings and capability/approximation labels. The response is disposable derived
data, never a format the browser can save as vehicle geometry. During an active
build only safe read-only/in-memory previews are allowed; they cannot write
build inputs or start another Blender subprocess outside the dispatcher.

## CVProvider interface prototype

Providers advertise their capabilities, available model identity/license and
execution location (`backend` or `browser_worker`). They are optional installed
adapters, never dynamic code from a project. Initial capabilities:

```text
segment_object(source_id, crop, seeds, parameters) -> MaskProposal
detect_edges(source_id, crop, parameters) -> EdgeProbabilityProposal
detect_wheels(source_id, crop, parameters) -> CircleOrEllipseProposals
suggest_landmarks(source_id, crop, allowed_semantics) -> LandmarkProposals
trace_contour(source_id, crop, seeds, parameters) -> VectorContourProposal
```

Each request/result uses the shared source/crop/revision/provenance envelope.
Methods support bounded work and cancellation; confidence is optional/qualified,
not calibrated ground truth. Masks may be local artifact blobs; vectors are
source pixels. Missing models or GPU support produce capability warnings and
leave manual tools usable. Provider proposals can be accepted only through
typed transactions. No model-specific branch enters core reconstruction.

## Pipeline job and result contract

`POST /runs` accepts `revision`, optional core `until` stage ID and `use_cache`.
Configured runtime choices are server capabilities, not user command strings.
The dispatcher checks save state, source/cage acceptance where required, stage
readiness and exact input hashes, then acquires the shared project lock for the
entire run. Initially serialize backend build requests globally; allow at most
one queued request for a project's current revision and make duplicate requests
idempotent. Another project's queued build is visible and cancellable.

| Order | Exact core stage ID |
|---|---|
| 01–04 | `preflight`, `references`, `calibration`, `overlay` |
| 05–08 | `cage`, `surfaces`, `silhouette`, `details` |
| 09–11 | `geometry`, `presentation`, `export` |
| 12–14 | `glb_verify`, `viewer`, `delivery` |

Stage `result` is absent/null while not finished; when present it is only PASS,
FAIL, SKIP or BLOCKED with the native reason and artifact IDs. Job `activity`
is separate transport/process metadata: QUEUED, RUNNING, CANCELLING, FINISHED,
INTERRUPTED. These words never replace stage results or enter core reports as
new result statuses. A cancelled active stage records FAIL with reason
`CANCELLED`; unexecuted dependents are BLOCKED. A job cancelled before it starts
has no fabricated successful stages and a BLOCKED outcome/reason. A restart
interrupts/fences unfinished jobs until their process state is reconciled.

The current Pipeline has printed results/final report but no structured observer
or cancellation service. A future generic optional observer reports stage start,
native result and artifact registration without web imports or altered gate
behavior. Runner changes manage child process groups (Windows Job Object or
platform equivalent), incremental log capture and cancellation. Do not parse
human stdout into invented PASS records. Keep the project lock until workers
have exited or are safely fenced; lease expiry/browser disconnect is not worker
termination. Rehash pinned inputs between stages and before export/delivery to
detect an external writer that ignored advisory locks.

## Events, logs and recovery

Example SSE record, not an existing event implementation:

```text
id: server-epoch:104
event: stage.result
data: {"project_id":"p-opaque","run_id":"j-opaque","revision":"sha256:...","stage":"calibration","result":"PASS","artifacts":["a-opaque"]}
```

Event names include `project.changed`, `project.conflict`, `lease.changed`,
`preview.ready`, `diagnostic.ready`, `run.activity`, `stage.started`,
`stage.result`, `run.log_available`, `artifact.ready` and `review.stale`.
Events carry epoch/sequence and subject revision. Apply idempotently, ignore
stale preview results, and use the current REST snapshot as recovery authority.
Persist a bounded runtime journal before announcing completion. Resume using
Last-Event-ID; an expired cursor or changed epoch requires snapshot resync, not
assumed delivery of missed events. Heartbeats maintain liveness without changing
stage results. Limit log chunk/event sizes and tell the client when older chunks
have rotated. Keep full core execution provenance under its existing policy.

Use one multiplexed stream per tab, with subscription caps; avoid a stream per
stage/view. Native EventSource uses the established same-origin HttpOnly session,
not bearer tokens in URLs. SSE's HTTP/1 connection limits and its one-way nature
are documented by [MDN](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events).
Use REST for cancellation, edits and snapshot fetches. Backpressure batches log
notifications and drops obsolete preview events, never terminal stage outcomes.

## Locking, file watching and migration

An editor lease is session/tab ownership, proposed TTL 30 s with 10 s renewals.
It is not the OS lock used by core/CLI mutations. Each save/checkpoint/review
transaction acquires the shared core lock; a build holds it until its workers
finish. Read-only views remain available. Lock metadata records owner/job/revision
for explanations, not authority to kill an arbitrary PID. CLI and Studio must
use the same cross-process locking/recovery implementation before writable Studio
release. Current v1 CLI has no such cooperative lock.

External file/Git changes trigger a hash check and `project.changed`/conflict
event. A missed watcher notification is caught by precondition rehash at save.
On dirty state, expose compare/reload/rebase commands; never last-writer-wins.
Shared transaction recovery handles interrupted multi-file saves before loading
project data. See the full crash guarantees in [data flow](studio_data_flow.md).

Unsupported future schemas return safe read-only capabilities rather than
attempting a lossy save. Migration preview returns the supported version pair,
hash-bound patch, backup/checkpoint identity, semantic issues and regression
requirements. Commit requires explicit intent and current revision. There is no
arbitrary migration script upload or automatic version bump on Open.

## Final review race protection

`GET /projects/{p}/validation` supplies a review subject digest covering geometry,
model inputs and the exact required proof hashes. The review screen retains it
while the operator inspects those images. `POST /projects/{p}/review` includes
that `inspected_evidence_digest`, reviewer, decision, notes and limitations.
Under the project lock, the backend compares the digest with current evidence
before invoking the standard core `record_review`. A changed proof/geometry
returns 409 even if project JSON revision stayed the same. The user must inspect
the changed evidence; the backend must not silently review the newest images
instead. The specialized writer derives record hashes from disk, not from
client-supplied replacement hash fields. Source/cage decisions use the same
subject-digest precondition for the evidence they accept.
