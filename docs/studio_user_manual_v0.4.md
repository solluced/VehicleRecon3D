# VehicleRecon Studio v0.4

Open a project and choose **Reference → Rectification**. Existing source authoring,
four-view editing, the Three.js cage, reviews and CV tools remain available.
Reconciliation works with CV disabled and needs no downloaded model or network service.

## Author a candidate

Choose the source and gauge views. The gauge image is a visual reference; measured
canonical correspondences and their world bindings provide the numerical evidence.
Changing the gauge selector does not solve or move world geometry.

The initial normalized domain spans the selected crop. Its endpoints are labelled
`domain_start` and `domain_end`; they are **not automatically identified axles**.
To normalize between known axles, open **Authoritative datum / domain change**,
explicitly confirm the change, and enter the independently calibrated image and
affine domain endpoints. The two locked normalized datums remain exactly 0/0 and
1/1. Relabel their semantic descriptions as appropriate.

The anchor table exposes semantic description, original pixel coordinate,
normalized source/target coordinates, role, confidence, provenance and measured
observation identity. Add/remove anchors, edit values, or drag unlocked handles on
the source image. Moving a bound anchor away from its measured coordinates makes
that candidate invalid; it does not change the measurement. Clear its binding to
make an explicitly manual FIT anchor instead. Never relabel an invented target as
independent measured evidence.

**FIT** anchors construct the mapping. **HELD_OUT** rows must bind measured,
observed canonical correspondences and never participate in fitting. At least two
independent held-out observations are required. Other critical correspondences
remain held out even when omitted from the editor. Each must meet its original
pixel tolerance and must not regress; an improved average cannot hide a failure.

Enter a creator and choose **Generate Candidate**. Each generation retains a new
archive record. Editing the draft does not update the displayed candidate report:
regenerate to evaluate it. Candidate generation changes no canonical calibration,
world geometry or review. Uncalibrated manual studies can inspect a manual mapping,
but lack the independent evidence needed for activation.

## Inspect the evidence

The mapping graph shows the identity baseline, FIT circles, HELD_OUT crosses and
locked datums. Correction can be displayed normalized, in source pixels, or as
**mm equivalent source correction**. That last quantity describes a calibrated
image-domain correction, not a change to the physical vehicle. It is unavailable
without a calibrated metric domain. The derivative graph labels the allowed band,
actual minimum/maximum and their analytic positions. Use Zoom +/−, Reset and drag
to pan; hover displays the exact core sample values.

The summary reports independent magnitudes and RMS values, local scale,
monotonicity, positive derivative and foldover status. Overhang ranges and their
corrections are separate from the between-datum report. SMALL / ACCEPTABLE,
BORDERLINE and EXCESSIVE describe distortion; numerical limits and failure text
are always visible. Borderline does not grant an exception to validation.

Preview modes are side-by-side, opacity, flicker and difference. The diagnostic
grid uses core mapping samples. Observed circles and projected crosses show the
residual change. The original image is never rewritten. Previews are disposable,
bounded, at most 1024 pixels on their longest side and support sources up to 16 MP.

The held-out table lists before/after residual, delta, tolerance and individual
PASS/FAIL. Historical Mark II records are labelled correction evidence rather than
claiming independent held-out residuals that were never recorded.

Use **Compare** on up to three archived candidates. Compare their anchors,
corrections, scale, held-out evidence, extrapolation and eligibility. Inspection
and comparison preserve all previous candidates. A canonical revision change
clears comparison selections so old summaries cannot look current.

## Decide and activate

An eligible candidate is **not active**. Inspect independent evidence, check the
explicit activation confirmation, then choose **ACTIVATE RECTIFICATION**. The core
rechecks the current revision, source hashes, calibration base, locks, scale,
extrapolation and held-out policy before its canonical transaction. A stale,
rejected, invalid, edited-but-not-regenerated or excessive candidate cannot activate.

Activation invalidates dependent reviews/readiness. It never ACCEPTS the source.
Inspect current evidence again in the multi-view review workspace and explicitly
choose ACCEPTED, NEEDS_CORRECTION or INCONSISTENT_SOURCE. **Undo rectification /
replacement** restores the exact previous canonical state, including review bytes;
the noncanonical candidate archive remains available. Normal undo/redo also works.

**REJECT CANDIDATE** requires a reason and keeps its evidence inspectable. Undo an
active calibration before rejecting its associated candidate. Archived reports
become STALE when their pinned source/calibration/revision changes. Refresh evidence
or reload after an external edit; regenerate before a new activation.

## Replace a source

Under **REPLACE / REGENERATE SOURCE VIEW**, explicitly confirm the selected view
and upload a PNG/JPEG. Studio hashes and retains the original encoded bytes under
an immutable project path. The old reference remains available. The new view is
marked CALIBRATION REQUIRED; old observations stay bound to the old source and
are excluded from current projection evidence. Candidates/reviews become stale,
coverage confirmation is withdrawn, and world coordinates stay fixed.

Compare retained old/new sources side-by-side or with opacity overlay. The landmark
transfer preview is a **proposal only**, using normalized whole-image coordinates.
It creates no observations and grants no measured status. Replacement framing must
be explicitly recalibrated before candidates can be generated. v0.4 does not add a
new calibration solver: a maintainer can use the existing core `SetCalibrationView`
operation to record inspected crop/basis and explicitly set source_state CURRENT.
It preserves reference history and never rebinds old observations to the new bytes.

## Mark II diagnostic

Open the legacy Mark II study read only. Its historical TOP relative to SIDE
candidate remains **REJECTED / NOT ACTIVE / OUTSIDE SCALE LIMIT**: approximately
42.037 px between axles, 236.902 px across the crop, RMS 73.163 px and local scale
0.518–2.150 against an allowed 0.90–1.10. Overhang extrapolation is visibly separate.
Activation has no override. This release does not resume Mark II surface work.

See [reconciliation contracts](reference_reconciliation.md) and
[development and measurements](studio_development.md).
