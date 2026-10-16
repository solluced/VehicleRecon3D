# ADR 0008 — Cancellation outcome conflicts with the locked API baseline

Status: **ACCEPTED — explicit operator decision, 2026-10-16**.
Date: 2026-10-16. Locked baseline: `58f13e8efe1ea9e7f8dea9ad93b3c4937a33d1ea`.
The operator accepted the recommended resolution in the follow-up architecture
decision. This ADR now supersedes the conflicting cancellation clauses of the
backend API. It does not by itself implement jobs or complete Studio v0.1A.

## Sources of the contradiction

The v0.1A Core Authoring Foundation handoff, section 1, states:

> If implementation exposes a real contradiction:
>
> STOP.
>
> Document it in a new ADR rather than working around the architecture.

Section 29 of that same handoff requires a cancelled run result of `CANCELLED`
and says not to confuse it with `FAIL`. It requires cancellation before process
start, during Blender and between stages. Section 28 places that result in the
managed-job contract.

The locked [backend API, Pipeline job and result contract](../studio_backend_api.md#pipeline-job-and-result-contract)
instead specifies:

- A cancelled active stage records `FAIL` with reason `CANCELLED`.
- A job cancelled before it starts has a `BLOCKED` outcome/reason.
- Completed stage results remain `PASS`, `FAIL`, `SKIP`, `BLOCKED`.

The headless core currently has those same four stage result values in
`vehiclerecon/core/pipeline.py`. It has no implemented managed-job cancellation
outcome that already reconciles these statements.

The precise counterexample is cancellation **before a job starts**: the new
handoff requires a cancelled run result, while the locked API explicitly calls
that job's outcome `BLOCKED`. Merely keeping four stage statuses and adding a
reason string does not satisfy the new separate cancellation outcome. Conversely,
changing the job outcome silently would reverse the locked API instruction.
Cancellation during a stage additionally needs a decision about whether an
interrupted stage is falsely categorized as a failure.

## Accepted resolution

Introduce a separate managed-job outcome, independent of native stage results:

| Concept | Proposed meaning |
|---|---|
| Native stage result | Preserve `PASS`, `FAIL`, `SKIP`, `BLOCKED`; never add `CANCELLED` to the existing enum |
| Managed job result | `SUCCEEDED`, `FAILED`, `BLOCKED`, `CANCELLED`; cancellation is distinct from genuine failure and blocking |
| Interrupted active stage | Retain any real completed result; otherwise no fabricated `FAIL` solely because cancellation interrupted execution |
| Unexecuted dependencies | May be reported `BLOCKED` with cancellation as cause, without changing the job result to `BLOCKED` |
| Job freshness | Independent current/stale input identity; cancelled or stale output is not promotable |

Keep process activity/lifecycle separate too. A cancellation request is not a
terminal result until owned workers have exited or been safely fenced. Cancellation
after an already finalized result must not rewrite that completed result.

This recommendation preserves the four pipeline stage statuses and existing v1
behavior while giving the new generic job abstraction its required distinct
cancellation result. It requires explicit supersession of the two cancellation
rules in the backend API, rather than pretending that baseline already says this.
No v1 project-name exception or Studio/web dependency is needed.

## Alternatives requiring a decision

1. Adopt the recommended separate job outcome and explicitly amend the locked
   cancellation clauses. Specify observer/log/result behavior in the core job
   contract and test cancellation at all three required points.
2. Retain the locked API rules. This requires revising v0.1A section 29 to allow
   the previous `FAIL`/`BLOCKED` cancellation outcomes; it does not satisfy the
   handoff as currently written.

The original proposed ADR/stop remains in Git history. The subsequent explicit
decision selects alternative 1 and authorizes continuing v0.1A. Cancellation
does not manufacture a stage FAIL. A real independently observed stage failure
retains FAIL and takes precedence over a later cancellation. Terminal job
outcomes are immutable. Freshness remains independent; cancelled and stale jobs
are never promotable. These rules require deterministic tests, including worker
termination, before claiming implementation complete.

## Work preserved and next validation

Only this ADR and its index entry are added. Core code, schemas, profiles,
project data, package dependencies, baseline evidence and existing architecture
documents remain unchanged. Mark II remains INCONSISTENT_SOURCE/BLOCKED with
surfaces/details NOT STARTED. FastAPI and React remain NOT STARTED.

No implementation tests or fresh Tesla reconstruction are claimed for this
documentation-only stop. On resolution, implement the v0.1A shared services in
reviewable commits and run the requested focused tests plus full exact-metric
Tesla regression. A recorded proposed resolution alone is not an implemented
authoring foundation.
