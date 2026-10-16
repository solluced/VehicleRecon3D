# ADR 0006 — Source observations and world geometry are separate

Status: selected architecture baseline for review; implementation pending.

## Context

The Mark II case demonstrates that observations of the same feature can be
incompatible across synthetic views. Moving a pixel annotation and moving a
shared world point are different authoring acts. A single source view also
does not constrain invisible world depth.

## Decision

Store source observations/vectors in canonical calibration/reference contracts
and one shared world cage in `cage.json`. A typed correspondence connects stable
observation IDs to named world landmark instances/point bindings. Profile roles
remain the core ontology. Add missing typed/stable-reference semantics through
generic core contract evolution, not a Studio-only map of authoritative XYZ.

Expose separate MoveObservation and MoveWorldLandmark commands. The former
changes original source pixels only. The latter changes one canonical XYZ and
reprojects all relevant views/instances with core calibration. A 2D world move
requires explicit axis/plane/depth or supported multi-view constraints. Report
projected-versus-observed dx/dy/residual/tolerance for each critical landmark.

## Alternatives

Per-view world points, silently using projections as observations, inferred
depth from a single drag, or averaging away critical failures would conceal
source conflicts. They are not selected. Inferred/occluded source features keep
their provenance and never masquerade as independent measured evidence.

## Consequences and verification

Selection links all views and 3D by semantic identity. Stable bindings survive
point insertion/split/merge or fail explicitly. Undo, external-edit conflicts and
shared symmetry are tested. Changing observation/calibration/world data stales
the relevant evidence and never preserves a review by rewriting its hashes.

See [data flow](../studio_data_flow.md) and [UI](../studio_ui_spec.md).
