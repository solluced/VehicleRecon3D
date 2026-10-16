# Longitudinal source-view audit

AFFINE RECTIFICATION: **FAIL**. Wheelbase **2.730 m**, axle X **-1.365/+1.365 m**, ground Z **0** remain fixed.

Coordinates are original source pixels. SIDE/TOP per-point and per-axle uncertainties remain 5/10 px. Intervals enumerate all endpoint combinations. Near-side homologous corners are compared; no world cage point was moved.

| Semantic | SIDE u / ratio | TOP u / ratio | TOP-SIDE | Error SIDE / TOP px | SIDE interval | TOP interval | Compatible |
|---|---:|---:|---:|---:|---|---|---|
| front_bumper | 367 / -0.299528 | 326 / -0.274468 | +0.025060 | 10.626 / 11.778 | -0.330918 to -0.269585 | -0.331111 to -0.222449 | PASS |
| front_axle | 494 / 0.000000 | 455 / 0.000000 | +0.000000 | 0.000 / 0.000 | 0.000000 to 0.000000 | 0.000000 to 0.000000 | PASS |
| hood_rear_cowl_near | 591 / 0.228774 | 571 / 0.246809 | +0.018035 | 7.647 / 8.476 | 0.205189 to 0.252358 | 0.204255 to 0.289362 | PASS |
| a_pillar_base | 591 / 0.228774 | 571 / 0.246809 | +0.018035 | 7.647 / 8.476 | 0.205189 to 0.252358 | 0.204255 to 0.289362 | PASS |
| a_pillar_roof | 692 / 0.466981 | 640 / 0.393617 | -0.073364 | 31.106 / 34.481 | 0.443396 to 0.490566 | 0.351064 to 0.436170 | FAIL |
| b_pillar_roof | 765 / 0.639151 | 777 / 0.685106 | +0.045955 | 19.485 / 21.599 | 0.615566 to 0.662736 | 0.642553 to 0.727660 | PASS |
| b_pillar_window | 759 / 0.625000 | 765 / 0.659574 | +0.034574 | 14.660 / 16.250 | 0.601415 to 0.648585 | 0.617021 to 0.702128 | PASS |
| c_pillar_roof | 835 / 0.804245 | 874 / 0.891489 | +0.087244 | 36.991 / 41.005 | 0.780660 to 0.827830 | 0.848936 to 0.934043 | FAIL |
| c_pillar_window | 891 / 0.936321 | 914 / 0.976596 | +0.040275 | 17.077 / 18.929 | 0.912736 to 0.959906 | 0.934043 to 1.020000 | PASS |
| rear_glass_roof_transition | 868 / 0.882075 | 884 / 0.912766 | +0.030690 | 13.013 / 14.425 | 0.858491 to 0.905660 | 0.870213 to 0.955319 | PASS |
| rear_axle | 918 / 1.000000 | 925 / 1.000000 | +0.000000 | 0.000 / 0.000 | 1.000000 to 1.000000 | 1.000000 to 1.000000 | PASS |
| rear_glass_lower_transition | 960 / 1.099057 | 981 / 1.119149 | +0.020092 | 8.519 / 9.443 | 1.073733 to 1.125604 | 1.073469 to 1.168889 | PASS |
| rear_bumper | 1072 / 1.363208 | 1117 / 1.408511 | +0.045303 | 19.209 / 21.292 | 1.331797 to 1.396135 | 1.351020 to 1.471111 | PASS |

The axle-constrained affine transform is SIDE u = TOP u * (424/470) + 83.531915. Two anchors exhaust both affine degrees of freedom. The internal discrepancies therefore cannot be removed by another longitudinal translation/scale. This conclusion depends on the stated semantic correspondences.

Cowl-near and A-base refer to the same physical intersection and are not independent checks. The centerline trunk edge cannot be measured independently in SIDE; the rear bumper supplies the rear-envelope observation. Aero edges are low confidence and excluded from fitting.

Sparse candidate fit: front/rear axles and A/B/C near-side roof intersections only. Cowl, lower window intersections, rear-glass transitions and bumpers remain held out. SIDE is a provisional reference gauge, not an independently measured orthographic truth.

The A-to-B span ratio intervals are SIDE 0.145161–0.200483 and TOP 0.238776–0.348889. Even their closest admissible pair needs at least 16.04% average local longitudinal compression in TOP relative to SIDE. A 10% local-scale limit is already infeasible before interpolation.
