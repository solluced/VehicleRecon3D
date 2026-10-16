> Historical first-pass notes. Current correction results: [cage_correction_report.md](cage_correction_report.md), [cage_residuals.md](cage_residuals.md).

# Mark II source observations

The standard CLI initialized this project with the existing `sedan` profile.
All three supplied images were imported unchanged and visually inspected.
Their SHA-256 identities match the source package's reference manifest.
No Python from that package was read, imported or executed.

At the user's request, official Toyota sources were researched. Toyota's
[E-JZX100 Tourer V catalog](https://toyota.jp/ucar/catalog/brand-TOYOTA/car-MARK_II/199609/1001095/)
and [eighth-generation history](https://www.toyota-global.com/company/history_of_toyota/75years/vehicle_lineage/car/id60013052/index.html)
agree on a 2.730 m wheelbase. This is the scale anchor, explicitly assuming
the illustrated X100-inspired drift chassis retains that spacing. It is not
a measurement of the custom build. Toyota's stock 4.760 x 1.755 x 1.400 m
envelope and 1.485/1.490 m tracks have not been imposed on the image geometry.
See `dimension_sources.json` for provenance and estimated custom dimensions.

`generated/reference_observations.json` records approximate original-pixel
landmarks and dimensionless proportions. Its first TOP axle estimates were
refined using an unmodified pixel crop; the visible upper/lower wheel centers
are partly occluded and do not share exact longitudinal positions. These
observations are authoring evidence, not an accepted four-view model gate.
The side view suggests a wheelbase/length ratio of about 0.60; source wheel
edges and centers have several pixels of uncertainty. The top panel shows side
faces and unequal upper/lower outlines, so its geometry needs a documented
cross-view consistency assessment. Calibration uses SIDE as longitudinal/height
authority and the agreeing FRONT/REAR extents for width. TOP receives a declared
1.1348 transverse affine rectification; no source image pixels are warped and
no threshold is lowered. The affine data and uncertainty are in calibration.json.

Approximate inferred custom envelope: length 4.54 m, width 2.04 m, height 1.24 m;
tire radius 0.309 m, wheelbase anchor 2.730 m. Width uncertainty is about 0.13 m;
the build's real track is unknown and the 1.75/1.77 m reconstruction tracks are
stance estimates. SIDE landmark uncertainty is approximately 5 px, TOP 10 px.
These are illustrative-source estimates with an external scale assumption.

The authored graph uses named bonnet, roof, deck, greenhouse, panel and bumper
boundaries, plus two real annular overfender surfaces. It has no whole-body
silhouette loft and no geometry copied from Tesla. Detail records are authored
for preflight but cannot execute until the independent four-view gate passes.

The framework, schemas and profiles remain identical to base commit
`060309de6014a760339ab100e4d61ecece102b72`. The unresolved source-scale
condition was resolved through documented source research. This does not
constitute a portability pass. The later explicit cage review failed; see
`cage_review.json` and `portability_findings.md`. Surface construction and
details were not executed after that decision.
