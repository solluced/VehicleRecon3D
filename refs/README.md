# Bundled reference set

All required references are present in this directory.

| File | Role | Authority |
| --- | --- | --- |
| `reference_multiview.png` | Clean perspective + FRONT/SIDE/REAR/TOP views | **Primary geometry source of truth** |
| `reference_surface_target.png` | Isolated clean semi-transparent blue-wireframe surface model | **Surface quality / topology / presentation target** |
| `reference_workflow.png` | Full reconstruction workflow; lower block #2 is the target surface-model benchmark | Process + quality target |
| `reference_dense_control_points.png` | Dense point/curve inference study | Secondary guidance |
| `reference_control_cage_overlay.png` | Control-cage/curve overlay study | Secondary guidance |

On conflict, follow `reference_multiview.png` for geometry and the surface target for topology/finish.
