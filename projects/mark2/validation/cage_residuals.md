# Mark II cage residuals — correction pass

Result: **FAIL**. Every row must pass individually; mean error is descriptive only.

66 critical observations: 44 PASS, 22 FAIL.
Maximum 52.273 px; mean 10.397 px.

Original primary-image pixels; actual Blender controls. SIDE/end uncertainty 5 px, TOP 10 px, unchanged.
Door cuts remain deferred because the preceding greenhouse/pillar checks fail.

| # | Semantic ID | View | Reference pixel | Projected pixel | dx | dy | Residual px | Uncertainty px | Pass |
|---:|---|---|---|---|---:|---:|---:|---:|---|
| 1 | front_axle_L | side | (494.00, 625.00) | (494.00, 625.00) | -0.000 | 0.000 | 0.000 | 5 | PASS |
| 2 | rear_axle_L | side | (918.00, 625.00) | (918.00, 625.00) | 0.000 | 0.000 | 0.000 | 5 | PASS |
| 3 | front_axle_L | front | (310.00, 623.00) | (314.07, 621.99) | 4.066 | -1.005 | 4.188 | 5 | PASS |
| 4 | front_axle_R | front | (35.00, 623.00) | (31.93, 621.99) | -3.066 | -1.005 | 3.226 | 5 | PASS |
| 5 | rear_axle_L | rear | (1133.00, 623.00) | (1129.03, 621.99) | -3.967 | -1.005 | 4.092 | 5 | PASS |
| 6 | rear_axle_R | rear | (1412.00, 623.00) | (1414.97, 621.99) | 2.967 | -1.005 | 3.133 | 5 | PASS |
| 7 | front_axle_L | top | (455.00, 1010.00) | (453.99, 1018.49) | -1.008 | 8.489 | 8.549 | 10 | PASS |
| 8 | front_axle_R | top | (460.00, 725.00) | (453.99, 731.15) | -6.008 | 6.149 | 8.597 | 10 | PASS |
| 9 | rear_axle_L | top | (925.00, 1026.00) | (929.71, 1018.79) | 4.714 | -7.212 | 8.616 | 10 | PASS |
| 10 | rear_axle_R | top | (926.00, 725.00) | (929.71, 727.57) | 3.714 | 2.574 | 4.519 | 10 | PASS |
| 11 | front_contact_L | side | (494.00, 673.00) | (494.00, 673.00) | -0.000 | 0.000 | 0.000 | 5 | PASS |
| 12 | rear_contact_L | side | (918.00, 673.00) | (918.00, 673.00) | 0.000 | 0.000 | 0.000 | 5 | PASS |
| 13 | front_contact_L | front | (310.00, 669.00) | (314.07, 669.00) | 4.066 | 0.000 | 4.066 | 5 | PASS |
| 14 | rear_contact_L | rear | (1133.00, 669.00) | (1129.03, 669.00) | -3.967 | 0.000 | 3.967 | 5 | PASS |
| 15 | hood_front_center_CENTER | top | (350.00, 875.00) | (350.00, 875.18) | 0.001 | 0.177 | 0.177 | 10 | PASS |
| 16 | hood_front_center_CENTER | front | (173.00, 572.00) | (173.00, 571.91) | 0.000 | -0.089 | 0.089 | 5 | PASS |
| 17 | roof_apex_CENTER | side | (733.00, 480.00) | (733.00, 481.01) | -0.000 | 1.010 | 1.010 | 5 | PASS |
| 18 | roof_apex_CENTER | front | (173.00, 482.00) | (173.00, 480.99) | 0.000 | -1.010 | 1.010 | 5 | PASS |
| 19 | roof_apex_CENTER | rear | (1272.00, 480.00) | (1272.00, 480.99) | 0.000 | 0.990 | 0.990 | 5 | PASS |
| 20 | trunk_rear_edge_CENTER | top | (1101.00, 875.00) | (1100.99, 872.59) | -0.008 | -2.409 | 2.409 | 10 | PASS |
| 21 | trunk_rear_edge_CENTER | rear | (1272.00, 549.00) | (1272.00, 547.80) | 0.000 | -1.204 | 1.204 | 5 | PASS |
| 22 | windshield_lower_corner_L | side | (591.00, 543.00) | (591.00, 542.07) | -0.000 | -0.930 | 0.930 | 5 | PASS |
| 23 | windshield_lower_corner_L | front | (276.00, 540.00) | (276.50, 540.78) | 0.500 | 0.784 | 0.930 | 5 | PASS |
| 24 | windshield_lower_corner_R | front | (69.00, 540.00) | (69.50, 540.78) | 0.500 | 0.784 | 0.930 | 5 | PASS |
| 25 | windshield_lower_corner_L | top | (571.00, 978.00) | (562.82, 979.86) | -8.175 | 1.855 | 8.383 | 10 | PASS |
| 26 | windshield_lower_corner_R | top | (569.00, 745.00) | (562.82, 769.03) | -6.175 | 24.033 | 24.814 | 10 | FAIL |
| 27 | a_pillar_roof_L | side | (692.00, 491.00) | (692.00, 491.23) | -0.000 | 0.233 | 0.233 | 5 | PASS |
| 28 | a_pillar_roof_L | front | (244.00, 491.00) | (243.00, 491.00) | -1.000 | 0.000 | 1.000 | 5 | PASS |
| 29 | a_pillar_roof_R | front | (104.00, 491.00) | (103.00, 491.00) | -1.000 | 0.000 | 1.000 | 5 | PASS |
| 30 | a_pillar_roof_L | top | (640.00, 944.00) | (676.15, 945.35) | 36.145 | 1.347 | 36.170 | 10 | FAIL |
| 31 | a_pillar_roof_R | top | (640.00, 765.00) | (676.15, 802.76) | 36.145 | 37.762 | 52.273 | 10 | FAIL |
| 32 | b_pillar_roof_L | side | (765.00, 489.00) | (765.00, 489.00) | -0.000 | 0.000 | 0.000 | 5 | PASS |
| 33 | b_pillar_roof_L | top | (777.00, 947.00) | (758.05, 969.27) | -18.950 | 22.272 | 29.243 | 10 | FAIL |
| 34 | b_pillar_roof_R | top | (774.00, 756.00) | (758.05, 778.27) | -15.950 | 22.272 | 27.394 | 10 | FAIL |
| 35 | c_pillar_side_roof_L | side | (835.00, 492.00) | (835.00, 492.00) | 0.000 | -0.000 | 0.000 | 5 | PASS |
| 36 | c_pillar_side_roof_L | top | (874.00, 947.00) | (836.59, 968.50) | -37.411 | 21.502 | 43.149 | 10 | FAIL |
| 37 | c_pillar_side_roof_R | top | (871.00, 757.00) | (836.59, 778.50) | -34.411 | 21.502 | 40.576 | 10 | FAIL |
| 38 | c_pillar_rear_roof_L | side | (868.00, 494.00) | (868.00, 492.45) | -0.000 | -1.553 | 1.553 | 5 | PASS |
| 39 | c_pillar_rear_roof_L | rear | (1202.00, 491.00) | (1201.00, 492.19) | -1.000 | 1.189 | 1.553 | 5 | PASS |
| 40 | c_pillar_rear_roof_R | rear | (1344.00, 491.00) | (1343.00, 492.19) | -1.000 | 1.189 | 1.553 | 5 | PASS |
| 41 | c_pillar_rear_roof_L | top | (884.00, 938.00) | (873.61, 945.69) | -10.385 | 7.685 | 12.919 | 10 | FAIL |
| 42 | c_pillar_rear_roof_R | top | (884.00, 764.00) | (873.61, 801.06) | -10.385 | 37.063 | 38.491 | 10 | FAIL |
| 43 | b_pillar_window_intersection_L | side | (759.00, 545.00) | (759.00, 545.00) | 0.000 | 0.000 | 0.000 | 5 | PASS |
| 44 | b_pillar_window_intersection_L | top | (765.00, 983.00) | (751.32, 993.30) | -13.682 | 10.295 | 17.122 | 10 | FAIL |
| 45 | b_pillar_window_intersection_R | top | (762.00, 744.00) | (751.32, 754.30) | -10.682 | 10.295 | 14.835 | 10 | FAIL |
| 46 | c_pillar_window_intersection_L | side | (891.00, 543.00) | (891.00, 543.00) | 0.000 | -0.000 | 0.000 | 5 | PASS |
| 47 | c_pillar_window_intersection_L | top | (914.00, 983.00) | (899.42, 992.79) | -14.579 | 9.785 | 17.559 | 10 | FAIL |
| 48 | c_pillar_window_intersection_R | top | (911.00, 744.00) | (899.42, 753.79) | -11.579 | 9.785 | 15.160 | 10 | FAIL |
| 49 | rear_glass_lower_corner_L | side | (960.00, 534.00) | (960.00, 530.00) | -0.000 | -3.998 | 3.998 | 5 | PASS |
| 50 | rear_glass_lower_corner_L | rear | (1181.00, 525.00) | (1181.50, 528.97) | 0.500 | 3.966 | 3.998 | 5 | PASS |
| 51 | rear_glass_lower_corner_R | rear | (1362.00, 525.00) | (1362.50, 528.97) | 0.500 | 3.966 | 3.998 | 5 | PASS |
| 52 | rear_glass_lower_corner_L | top | (981.00, 961.00) | (976.84, 965.19) | -4.162 | 4.190 | 5.906 | 10 | PASS |
| 53 | rear_glass_lower_corner_R | top | (983.00, 754.00) | (976.84, 780.85) | -6.162 | 26.848 | 27.546 | 10 | FAIL |
| 54 | front_door_leading_edge_L | side | (591.00, 648.00) | (558.45, 645.04) | -32.546 | -2.956 | 32.680 | 5 | FAIL |
| 55 | front_door_upper_leading_edge_L | side | (591.00, 550.00) | (583.30, 551.86) | -7.696 | 1.857 | 7.917 | 5 | FAIL |
| 56 | b_pillar_lower_attachment_door_separator_L | side | (770.00, 639.00) | (747.93, 645.04) | -22.066 | 6.044 | 22.879 | 5 | FAIL |
| 57 | rear_door_trailing_edge_L | side | (878.00, 642.00) | (855.10, 645.04) | -22.901 | 3.044 | 23.103 | 5 | FAIL |
| 58 | body_lower_line_L | side | (706.00, 659.00) | (706.00, 659.00) | 0.000 | -0.000 | 0.000 | 5 | PASS |
| 59 | windshield_lower_center_CENTER | front | (173.00, 539.00) | (173.00, 539.00) | 0.000 | 0.000 | 0.000 | 5 | PASS |
| 60 | windshield_lower_center_CENTER | top | (534.00, 858.00) | (554.11, 874.47) | 20.112 | 16.474 | 25.998 | 10 | FAIL |
| 61 | windshield_upper_center_CENTER | front | (173.00, 489.00) | (173.00, 489.00) | 0.000 | 0.000 | 0.000 | 5 | PASS |
| 62 | windshield_upper_center_CENTER | top | (632.00, 858.00) | (670.92, 874.07) | 38.918 | 16.072 | 42.106 | 10 | FAIL |
| 63 | rear_glass_upper_center_CENTER | rear | (1272.00, 485.00) | (1272.00, 485.00) | 0.000 | 0.000 | 0.000 | 5 | PASS |
| 64 | rear_glass_upper_center_CENTER | top | (880.00, 855.00) | (868.39, 873.39) | -11.613 | 18.392 | 21.752 | 10 | FAIL |
| 65 | rear_glass_lower_center_CENTER | rear | (1272.00, 525.00) | (1272.00, 525.00) | 0.000 | 0.000 | 0.000 | 5 | PASS |
| 66 | rear_glass_lower_center_CENTER | top | (1000.00, 859.00) | (990.78, 872.97) | -9.222 | 13.971 | 16.740 | 10 | FAIL |

See reference_discrepancies.md and reference_consistency.json for the independent, non-overlapping A–B roof/wheelbase intervals.
The canonical four-view PNGs are annotated derivatives of the archived CLI overlays, at 1:1 image pixels.
Occluded/undefined source landmarks are not fabricated.
