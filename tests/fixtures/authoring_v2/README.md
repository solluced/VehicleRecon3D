# Consistent synthetic v2 authoring fixture

A blank 256x256 source and four analytic affine views observe the same named
world landmark. Coordinates, dimensions and provenance are synthetic test data,
not an automobile reconstruction or inferred OEM measurements. The fixture has
stable source/curve IDs and a shared landmark reference, with exact zero-pixel
reprojection residuals apart from floating-point roundoff.

Included source/cage review records were explicitly recorded through the shared
authoring service for this analytical fixture. They are not inferred from a
successful curve construction; tests also exercise absent/rejected/stale records.
This draft does not
claim complete surface/detail/build configuration or a deliverable vehicle.
