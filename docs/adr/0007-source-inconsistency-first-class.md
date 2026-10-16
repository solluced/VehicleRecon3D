# ADR 0007 — Source inconsistency is a first-class result

Status: selected architecture baseline for review; implementation pending.

## Context

Not every AI-generated multiview is a valid reference for one world-space car.
Mark II's attempted TOP warp has local scale 0.518–2.150 and remains rejected.
Current cage-construction PASS does not itself certify multi-view acceptance.

## Decision

Provide reference-authoring dispositions ACCEPTED, NEEDS_CORRECTION and
INCONSISTENT_SOURCE. They are separate from pipeline PASS/FAIL/SKIP/BLOCKED and
the standard final visual review. Store explicit core-readable decisions with
current source/observation/calibration/provenance/limit hashes. New authoring
contracts require current source and cage acceptance before surfaces in both
CLI and Studio; a disabled UI button alone is insufficient.

Source rejection leaves active calibration/world geometry unchanged. A candidate
preview is not activation. Exact axle anchors, positive monotonic derivatives,
declared local-scale limits, magnitude/extrapolation and held-out checks remain
visible. Extreme candidates cannot be auto-accepted or made acceptable by
silently changing tolerances or geometry independently per view.

## Alternatives

Forcing a model from every source, relabelling a rejected warp active, or treating
an average residual as acceptance would conceal invalid input. A GUI-only gate
would disagree with CLI. These alternatives are not selected.

## Consequences and verification

Mark II is a valid rejection regression, not a completed vehicle. The architecture
phase changes none of its data/evidence or NOT STARTED stages. Implement the new
gate with generic versioned contracts; legacy v1 behavior/coverage and explicit
migration policy are described in the roadmap, with no project-name exemption.
Test rejection/reopen, stale evidence, independent critical failures and headless
surface blocking. Existing final visual review remains separately required.

See [product case](../studio_product_spec.md#mark-ii-motivating-case) and
[roadmap compatibility](../studio_roadmap.md#foundation-before-writable-studio).
