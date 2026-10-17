# Reference reconciliation

The authoritative implementation is `vehiclerecon/reference/reconciliation.py`
and the existing `PiecewiseMonotonicAxisWarp` / `AxisRectification` in core.
TypeScript displays core samples and never implements PCHIP, its inverse or an
independent eligibility rule.

## Contracts and state

`reconciliation_request.schema.json` specifies the source/gauge, axis, domains,
2–64 anchors, maximum scale change and extrapolation policy. The generic
`rectification_candidate.schema.json` accepts its original canonical variant and
the new `record_type: reference_reconciliation` archive variant. Original v2
candidate commands and existing projects stay compatible. New records capture
creator, algorithm/version, source revision, all reference hashes, calibration
hash, crop, complete parameters, FIT/HELD_OUT IDs and frozen measured evidence.

Studio archives inactive analysis in `.studio/rectification/<opaque-id>.json`.
These records are outside canonical revision/history: generation and rejection
cannot modify calibration, cage or accepted reviews. State is DRAFT while edited
locally, EVALUATED or ELIGIBLE_FOR_ACTIVATION after evaluation, REJECTED after an
explicit reason, and ACTIVE after an explicit core transaction. STALE is an
effective freshness state. Installed rectification can remain installed while its
candidate evidence is stale; the API distinguishes `active` from `freshness`.

Reports and previews are derived, disposable caches. The archive is bounded to
256 records per project / 256 KiB per record, reports to 16 MiB / 24 entries and
PNG previews to 16 MiB / 16 entries. Archive listing returns compact summaries;
the full report is fetched on inspection, with at most three frontend comparison
records retained. Full source bytes remain ordinary immutable project references.

## Core eligibility

Only FIT anchors construct the monotone mapping. There must be exactly two locked
FIT datums with exact normalized pairs (0,0) and (1,1). Domain changes require a
separate explicit confirmation. Increasing domains, unique source coordinates,
strictly increasing targets and strictly positive derivatives are mandatory.

The maximum requested scale change cannot exceed 0.10. The accepted analytic band
is `[1-limit-1e-12, 1+limit+1e-12]`; the 1e-12 epsilon is a numerical boundary
policy, not a user-adjustable tolerance. Core computes exact derivative extrema
over fitted support and the crop. Positive linear tails are reported as
extrapolation. Unsupported crop regions require explicit opt-in and cannot exceed
half the crop. Front/rear overhang correction is audited separately.

Bound anchors must exactly match current measured canonical evidence within a
1e-9 coordinate consistency epsilon. An observation cannot be both FIT and
HELD_OUT or counted twice. Every remaining critical correspondence participates
in held-out evaluation. At least two distinct measured held-outs are required;
each must satisfy its own unchanged original source-pixel tolerance, each must
not regress, aggregate held-out RMS must improve, and no critical failure may
remain. Residuals use inverse candidate world projections back into original
source pixels, preserving the meaning of the existing tolerance policy.

Metric equivalent correction uses the calibrated **affine domain span** along the
chosen axis, not an assumed wheelbase for a vertical/lateral axis. Without full
metric calibration it is unavailable. Legacy Mark II uses its recorded 2.730 m
wheelbase datum. Correction RMS is distinct from residual RMS.

## Transaction boundaries

`ActivateRectification` recaptures current canonical correspondence evidence and
reevaluates it inside the shared authoring transaction. It does not trust a
browser report or frozen archive scores. Exact revision/hash/crop fences,
locked datums and the full eligibility policy are enforced again. Only the
selected view's rectification is written; existing invalidation stales reviews,
residuals and dependent stages. Source review acceptance remains independent.
Core undo restores exact previous canonical bytes/revision and review state;
archive evidence is retained. Studio activation also requires a lease, CSRF,
matching If-Match and explicit confirmation, with normal idempotency behavior.

`ReplaceSourceView` uses the existing project-scoped validated PNG/JPEG upload,
an immutable hash-named path and an explicit confirmation. It retains the old
reference and source/crop history, binds the selected view to a new reference
role, removes its old warp, marks calibration required and clears coverage
confirmation. Old observations and world geometry remain unchanged. Registration
checks exclude observations belonging to the previous active source. Undo restores
canonical state while imported bytes remain retained. Calibration edits preserve
the replacement role/history/staleness unless explicitly supplied otherwise.

No endpoint accepts arbitrary paths, URLs, shell/Python programs or remote model
downloads. Image serving uses existing opaque reference identities and path guards.
Previews hash-check their pinned source and use core inverse mapping on the server.

## Verification

`tests/reconciliation_fixture.py` creates an analytical positive grid source in a
private directory: source knots 0/.3/.65/1, target 0/.31/.64/1, independent
held-outs .15/.45/.8, a 180 px / 3.6 m affine domain. No vehicle geometry is invented.
Tests cover eligibility, individual held-out regression, exact limits, invalid
domains/knots, source/crop/calibration staleness, review invalidation, explicit
activation, exact undo, replacement and immutable protected projects.

Browser tests exercise the manual positive path with CV disabled, graph/preview
inspection, activation/undo, stale rejection, replacement and the read-only Mark II
failure. Existing source/CV/multi-view/gizmo/performance browser scenarios remain
required. Release evidence is indexed under `validation/studio_v0.4`.
