# Development evidence

The previous starter had no images; the continuation package supplied all five. Their existence, decoded dimensions and original hashes were verified before geometry work.

The first cage overlay showed square nose/tail sections in plan view. Those sections were narrowed and the shoulder rails reconciled. The first body mask comparison measured side 0.8975, top 0.9254, front 0.8941 and rear 0.9047 IoU. Wheelhouse backing, window-frame joins, front lip and greenhouse registration were corrected before further detailing.

Reflection inspection exposed cowl/rear-quarter interpolation overshoot. Shape-preserving tangents and controlled transverse fender roll replaced the offending interpolation. The first detailed headlights were too vertical; they were moved to the cheek patches. Rims were inset into the tire profile and brake discs moved behind the spokes.

A refinement script initially assumed vertex indices survived a cleanup weld. It raised IndexError and prevented later presentation objects from being created. The cowl update now rebuilds its control grid, the bridge is integrated into the fender boundary, and Blender commands use --python-exit-code 1. The corrected pipeline completed without Python exceptions and the saved project contains all 24 topology overlays.

Browser screenshots exposed incorrect canvas alpha composition, which was corrected to an opaque neutral canvas with transparent glass rendered over it. Rear lamp returns were seated against the evaluated hatch surface after a final screenshot showed one standing proud. Geometry checks, renders, exports and browser QA were regenerated after these corrections.

Intermediate diagnostic logs remain locally under validation/*.log and are excluded from Git. The final structured reports and proof renders are tracked.
