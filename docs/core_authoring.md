# Core authoring foundation v0.1A

This is a transport-independent Python API implementing the core prerequisites
of the locked Studio architecture. No FastAPI, React, editor database, browser
geometry format or automatic vehicle reconstruction is introduced. HTTP leases,
authentication, sessions, proposal providers and the production editor remain
future work.

## Versions and canonical ownership

v1 remains the legacy reconstruction contract. Opening/building Tesla does not
migrate it or manufacture v2 acceptance. v2 is an explicit authoring contract
with DRAFT/READY state. Drafts allow null dimensions, missing views and incomplete
build inputs. READY adds structural requirements and never substitutes for
review. Unsupported future versions are reported read-only and refused for edits.

Canonical filenames remain `project.json`, `generated/calibration.json` and
`generated/cage.json`. Root `generated` paths select the other core contracts.
New schemas are `project_v2`, `calibration_v2`, `cage_v2`, shared `authoring`,
`authoring_command`, `authoring_review` and `rectification_candidate`. Existing
v1 schemas/semantics remain intact. No project-name exceptions exist.

Calibration owns typed source objects in view `landmarks.observations` and
`landmarks.source_curves`: point, polyline, spline, circle, measurement and axis.
Objects carry stable ID, view/role, original image coordinates, reference ID/SHA,
crop identity, revision, provenance, uncertainty, visibility and measured flag.
Source knots use stable IDs and optional pixel handles. Inferred, occluded and
unobserved are explicit; unknown coordinates are not zero residual. Measurements
record value (including null), unit, meaning, provenance and optional lock/error.

Cage landmarks own shared XYZ. Curves have stable `point_ids` and may reference
named shared landmarks. Calibration `correspondences` bind an observation/revision
to a world landmark or stable curve knot, with optional observed knot, side,
semantic role, provenance and explicit pixel tolerance. No view owns a separate
world XYZ copy. Broken IDs, stale bytes/crops/revisions, conflicting links and
invalid knots fail. Insertion and split/merge preserve identity; ambiguous deletes
fail rather than rebinding by index. Shared split endpoints retain one ID/value.

## Read-only services and acceptance

`Workspace(root)` supplies validated raw documents and revision.
`authoring.projection` exposes `project_world`, `batch_projection`, `residual`,
`residual_report` and `sample_cage` without Blender. Residuals report
projected-minus-observed dx/dy, Euclidean distance, tolerance and status. Every
required/critical check passes individually; averages cannot hide failures.
Coverage must be explicitly confirmed with critical links/required views.
Confidence does not increase tolerance.

Feedback samples include entity/role, stable controls and visibility. VECTOR
curves use piecewise linear sampling. AUTO curves return their control polygon,
explicitly approximate: Blender resolves final handles and surfaces.
`readiness(root)` reports structured states/reasons without building anything.
`invalidation(scopes)` follows native stage dependencies: source/calibration edits
stale source/cage reviews; world edits stale cage review; viewer-only changes
preserve geometry; inactive candidates cannot activate geometry/calibration.

| Canonical review | Decisions | Subject/evidence |
| --- | --- | --- |
| `validation/source_review.json` | ACCEPTED, NEEDS_CORRECTION, INCONSISTENT_SOURCE | References, calibration/observations/correspondences/policy, dimensions/profile, proof hashes and coverage |
| `validation/cage_review.json` | ACCEPTED, NEEDS_CORRECTION | Source subject/decision, cage bytes, individual residuals and proof hashes |

`reviews.subject(workspace, kind)` identifies inspected evidence. ACCEPTED
commands require this `expected_subject`, reviewer and notes; replaced evidence
conflicts. Acceptance is not inferred from construction. Cage acceptance requires
current source acceptance and passing critical residuals. Source disposition is
a human decision, not an automatic mathematical consistency certificate.

For v2, SURFACES checks both current ACCEPTED reviews before cache lookup and in
direct execution. Missing/stale/negative decisions block it. Existing v1 final
visual-review/export gates remain unchanged.

## Commands, history and migration

```python
from vehiclerecon.authoring.service import AuthoringSession

session = AuthoringSession(root)
result = session.apply([
    {"type": "MoveWorldLandmark", "world_entity_id": "roof_corner",
     "point": [0.0, 0.5, 1.0]}
], expected_revision=session.revision)
session.undo(expected_revision=result["revision"])
session.redo(expected_revision=session.revision)
```

The typed schema is the API boundary, rather than arbitrary JSON patches or
project code. Command families:

- Add/Move/DeleteObservation; Add/Move/DeleteWorldLandmark.
- BindObservation/UnbindObservation.
- Add/Move/DeleteSplinePoint; SplitSpline/MergeSpline for source or cage.
- SetMeasurement (optionally updating a dimension); SetTolerance.
- SetSourceDisposition; SetCageReview; SetCoveragePolicy.
- SetCalibrationView; SetViewerLabel; bounded SetProjectSettings sections.
- SetProjectMetadata; SetObservationProperties, preserving stable identity.
- RegisterReference through `authoring.imports.import_reference`: exact immutable
  source bytes, computed SHA/dimensions and source-only view crops, with no invented
  affine/metric calibration. Decoders enforce their own import resource budgets.
- AddRectificationAnchor/RemoveRectificationAnchor for inactive candidates.

Commands check expected revision/IDs, apply in memory, validate schemas/source
identities/cross-file semantics and commit once. Source moves cannot change world
XYZ; world moves cannot change source pixels. Live-session undo/redo uses exact
before/after deltas and revision checks. External changes require reload/conflict
resolution; restored hash-equivalent state still passes normal review checks.

Inactive candidates use `validation/rectification_candidates/<id>.json`, with
base calibration identity/revision and locked datum anchors. Active calibration
enforces existing invertibility/local scale limits. Candidate editing does not
implement automatic fitting or approval.

```powershell
python -m vehiclerecon init projects/new_draft --schema-version 2
python -m vehiclerecon authoring-status projects/new_draft
python -m vehiclerecon migrate projects/copy --to 2 --dry-run
python -m vehiclerecon migrate projects/copy --to 2 --expected-revision <digest>
```

`authoring.versions` inspects/previews and explicitly migrates after recording a
checkpoint of original documents/source hashes. Results list changed files,
old/new hashes, warnings and required manual work. Numeric geometry is preserved;
knot IDs are deterministic. Missing observations/measurements stay missing,
coverage is unconfirmed, and old unversioned source/cage decisions are archived
rather than accepted. Source bytes remain immutable. Test migration on a copy.

## Revisions, locks and recovery

`core.revisions.revision(root)` hashes sorted exact-byte identities of root
project, configured authored JSON, immutable references, explicit decisions and
inactive candidate records (missing files have null identity). Decisions/candidates
are canonical authoring state with narrower geometry cache scopes. UI state,
reports, cache and timestamps are excluded. Review subjects exclude their own
decision to avoid cycles. Derived proof bytes have independent subject/job hashes;
proof replacement need not change the geometry revision.

`ProjectLock` uses Windows OS byte locks or POSIX flock, with PID/thread,
operation, acquired revision and UTC diagnostics. Same-thread nesting is allowed;
competing threads/processes receive a lock conflict. CLI builds, project
read/recovery, authoring, migration, review writers and jobs share it. A Blender
parent holds the lock through worker lifetime; its trusted worker reads that
snapshot without reacquiring the parent's exclusive lock. `worker_snapshot` is
an internal worker capability, not a general validation bypass. OS release on
exit matters; stale diagnostic metadata alone does not mean a live lock.

`core.transactions.commit` backs typed services: validate complete candidate
documents, recheck revision, fsync old/new journal bytes/hashes and intent,
atomically replace files, then publish commit. Journals/pending marker live in
`.cache/authoring/`. Normal failure rolls back; next locked open recovers a crash
to consistent new state. Recovery verifies destinations and rechecks each before
writing. Unexpected third-party bytes block recovery without overwriting them.
Shared-lock readers cannot see partial commits. An external editor ignoring locks
can still race filesystem writes; hashes detect conflicts, rather than promising
filesystem-wide isolation. Journal retention/pruning is future policy.

## Events and managed jobs

`Events` supplies optional copied/sequenced project, validation, stage, progress,
log, artifact and job events. Observer errors are isolated diagnostics, never
post-commit failures. No observers is a supported mode.

```python
from vehiclerecon.core.jobs import JobManager

manager = JobManager(observers=(events.append,))
job = manager.submit(root, until="calibration", expected_revision=revision)
manager.run(job.job_id)        # Synchronous dispatcher; caller may use a thread.
manager.cancel(job.job_id)     # Thread-safe request or finalized no-op.
pointer = manager.current(root)
```

Submission pins revision, exact input/proof hashes and implementation identity.
Execution uses isolated `.cache/jobs/<id>/workspace` and reuses only verified
cache bytes. Results/logs remain run-scoped. Successful, current, hash-verified
results may publish `.cache/jobs/current.json`, pointing to workspace artifacts.
Failed/blocked/cancelled/stale/corrupt results cannot replace that pointer.
Promotion/current reads recheck inputs, proofs, implementation and artifacts.
No incomplete job copies output over a prior CLI delivery; existing CLI output
paths remain unchanged. Future adapters resolve artifacts through this registry.
The manager serializes dispatch; OS project locks coordinate other managers and
CLI. Journals persist diagnostics, not geometry. Restart/resume and HTTP/SSE are
future adapters.

Cancellation follows accepted [ADR-0008](adr/0008-cancellation-job-outcome-conflict.md):

| Dimension | Values |
| --- | --- |
| Native stage result, unchanged | PASS, FAIL, SKIP, BLOCKED |
| Managed terminal outcome | SUCCEEDED, FAILED, BLOCKED, CANCELLED |
| Job activity | QUEUED, RUNNING, CANCELLING, FINISHED |
| Freshness, independent | current, stale |

Queued/pre-first cancellation creates no failed stage. Between stages, completed
results remain. Active interruptions have separate INTERRUPTED activity records,
not artificial FAIL. Terminal CANCELLED requires owned worker exit/fencing. Real
independently observed stage/worker failure precedes later cancellation. Finalized
results are immutable; late cancel is a no-op. Native partial reports retain the
existing BLOCKED summary plus interruption/unexecuted records, while the managed
outcome is CANCELLED.

Windows owned processes start suspended, join a kill-on-close Job Object, then
resume. Assignment failure kills the suspended child, with no unfenced fallback.
POSIX workers use owned process groups. Stdout/stderr drain concurrently with
bounded capture. Cancel terminates the owned tree and joins readers before the
terminal outcome. In-process Python stages cooperate at checks/stage boundaries;
uncooperative functions remain CANCELLING until return, without force-killing
Python threads.

Implementation sources: [Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects),
[job assignment](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject),
[job limit information](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information),
[Python subprocess](https://docs.python.org/3/library/subprocess.html).

## Validation scope

`tests/fixtures/authoring_v2` is an independent analytical four-view fixture with
explicit source/cage acceptance and shared world controls. It proves authoring
semantics and gate behavior, not a completed vehicle or final surface build.
Negatives cover missing/stale reviews, rejected source, individual failures,
extreme warps, broken IDs, conflicts, crash recovery and cancellation races,
including real Blender. Full cold Tesla v1 regression is separate; Mark II's
rejected source/candidate remain protected without migration/body modeling.
Phase evidence is in `validation/studio_v0.1a/`; large isolated runs stay under
ignored `build/` instead of rewriting either vehicle project.
