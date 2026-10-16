# Consistent synthetic v2 authoring fixture

A blank 256x256 source and four analytic affine views observe the same named
world landmark. Coordinates, dimensions and provenance are synthetic test data,
not an automobile reconstruction or inferred OEM measurements. The fixture has
stable source/curve IDs and a shared landmark reference, with exact zero-pixel
reprojection residuals apart from floating-point roundoff.

Review records are generated explicitly by authoring acceptance tests/services;
they are not inferred from a successful curve construction. This draft does not
claim complete surface/detail/build configuration or a deliverable vehicle.
