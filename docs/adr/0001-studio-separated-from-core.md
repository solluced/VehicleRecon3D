# ADR 0001 — Studio separated from reconstruction core

Status: selected architecture baseline for review; implementation pending.

## Context

VehicleRecon3D is an existing regression-proven Python/Blender compiler. Visual
authoring should reduce per-vehicle manual JSON/Python work while preserving
headless execution and a single implementation of reconstruction and validation.

## Decision

Create an optional `studio/` workspace with a browser frontend and separately
packaged Python backend. It imports reusable core services. Core never imports
Studio, UI or CV libraries. A future lazy `vehicle-recon studio` subcommand loads
the optional distribution; ordinary `python -m vehiclerecon ...` stays independent.
Schema-derived clients carry contracts, not a second geometry engine.

## Alternatives

Embedding UI services/dependencies in core would complicate CLI/CI and ownership.
A second TypeScript reconstruction engine would drift in curve math, gates and
cache behavior. A Blender-only authoring UI would not meet browser-first image
editing requirements. These are not selected.

## Consequences and verification

Generic missing services belong in separate core increments, with tests and
Tesla regression. Studio transports intent and displays evidence. Core installs
and unit tests work with Studio absent; optional Studio tests have their own job.
New GUI dependencies never become mandatory for batch reconstruction. The
current phase creates documentation only; no backend/frontend modules are added.

See [architecture](../studio_architecture.md) and [roadmap](../studio_roadmap.md).
