# Reference dimensions — calibration required

Status: **READY FOR CALIBRATION — source images bundled**.

Do not copy nominal dimensions from the handoff as if they were measured values. Measure normalized ratios from `refs/reference_multiview.png`, reconcile FRONT/SIDE/REAR/TOP, then choose/record a physical scale.

| Quantity | Measured value | Normalized by length |
| --- | --- | --- |
| Overall length | Pending calibration | 1.000 |
| Overall width | Pending calibration | Pending |
| Overall height | Pending calibration | Pending |
| Wheelbase | Pending calibration | Pending |
| Wheel radius | Pending calibration | Pending |
| Front overhang | Pending calibration | Pending |
| Rear overhang | Pending calibration | Pending |
| Front track | Pending calibration | Pending |
| Rear track | Pending calibration | Pending |

Coordinates: X longitudinal, front negative X; Y lateral; Z up; ground at Z=0.

Required calibration output:
- view crop transforms / pixel dimensions;
- wheel-center coordinates in each applicable orthographic view;
- centerline / ground / roof / extremity landmarks;
- cross-view inconsistency notes;
- selected physical scale and justification;
- `validation/reference_alignment.png`.
