# Reference calibration
All five original PNGs were opened, decoded and checked against refs/manifest.json. Pixel sizes: multiview, surface target and workflow 1536 × 1152; both secondary studies 1448 × 1086. Original files are unchanged. See validation/reference_inventory.json.

Registration status: PASS for a common landmark coordinate system, with documented source inconsistencies. This is an illustrative multiview sheet, not an exact orthographic engineering drawing. No completed body validation is implied.

| Quantity | Ratio to length | Chosen scale, m | Basis |
| --- | ---: | ---: | --- |
| Length | 1.00000 | 4.800 | Assumed scale only |
| Body width, excludes mirrors | 0.39216 | 1.882 | Top 280 / 714 px |
| Height | 0.31787 | 1.526 | Side 233 / 733 px |
| Wheelbase | 0.64120 | 3.078 | Side (990 − 520) / 733 px |
| Tire radius | 0.08458 | 0.406 | Mean side radius 62 / 733 px |
| Front overhang | 0.17053 | 0.819 | Side (520 − 395) / 733 px |
| Rear overhang | 0.18827 | 0.904 | Side (1128 − 990) / 733 px |
| Front track | 0.3354 | 1.610 | Rectified front wheel centers, approximate |
| Rear track | 0.3417 | 1.640 | Rectified rear wheel centers, approximate |

Coordinates: front −X, rear +X, Y lateral, Z up, ground Z=0. Side mapping: X=(u−761.5)×4.8/733, Z=(741−v)×4.8/733. Top mapping: X=(u−760)×4.8/714, Y=(932−v)×1.88235294/280. Exact crops and raw landmarks are in refs/reference_data.json.

Side extents (395,508)–(1128,741); axle centers (520,679), (990,681). Top body extents (403,792)–(1117,1072). Front body extents (25,508)–(353,741), centerline u=189. Rear extents (1185,508)–(1517,741), centerline u=1351. Landmark uncertainty approximately ±3 pixels; shadows excluded.

## Source conflicts and resolution
Front image width/height=328/233=1.408, while side/top yield 1.234. Front horizontal registration therefore uses approximately 0.876 of the uniform side-based scale. Rear uses its own measured body width to register to the same 1.882 m envelope. These anisotropic corrections are explicit: they do not demonstrate that the unrectified sheet is geometrically consistent.

Front and rear side-view tire radii are approximately 64 and 60 pixels (6.45% difference relative to their mean). Use a common 62 px radius and ground-based axle height, rather than encoding the apparent tire mismatch into the model. Top axle registration is inferred from the side: wheels are not visible in the top view. Side mirror placement and apparent roof perspective are approximate. Preserve this uncertainty during validation.

## Alignment proof
validation/reference_alignment.png combines four actual Blender camera renders of the calibrated image planes with centerline, ground, envelope and axle datums. Individual alignment_SIDE/TOP/FRONT/REAR renders use lowercase filenames. Planes have packed cropped textures; original full-resolution references are also loaded. All references are hidden for geometry-only validation and can be unhidden for inspection.

