# ADR 0002 — Canonical data remains existing project JSON

Status: selected architecture baseline for review; implementation pending.

## Context

The CLI already consumes project, calibration, cage, bounded surface graph,
details and silhouette-trace files. Renderer libraries often offer their own
serialization, which would create an incompatible second model if adopted.
Current v1 also lacks typed generic authoring observations and stable bindings.

## Decision

Studio edits the same configured canonical files, validated by the same core
schemas and semantic checks. There is no `studio_project.json`. Renderer objects,
preview buffers and generated TS types are derived. `.studio/session.json`
holds UI preferences only. Recovery/checkpoints are clearly labelled backups
or command deltas and are never alternate compiler inputs.

Add missing authoring capabilities through reviewed generic core contracts and
explicit versioned migrations in this JSON family. Retain v1 support; unsupported
future versions open read-only. Unknown OEM measurements remain unknown in a
validated draft, not fabricated positive numbers. The current schemas are not
changed by this architecture phase.

## Alternatives

Konva/Fabric scene JSON, a Studio database of authoritative geometry, or storing
accepted observations only in UI session state would break CLI roundtrips.
Silently adding untyped fields to v1 would hide unsupported semantics. None is
selected. A database may index disposable runtime jobs, not own vehicle geometry.

## Consequences and verification

Save uses revision-checked, schema/semantic-validated transactions and shared
CLI/backend locks. Source bytes stay immutable. A saved project opens through
the core without Studio, and deleting UI state loses no accepted geometry.
Migrations need backups, diffs, compatibility tests and Tesla regression.

See [data flow](../studio_data_flow.md).
