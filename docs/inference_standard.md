# Inference Sheet Standard v1

Automobiles only. Preserve original input bytes and record decoded dimensions
and SHA-256. The primary multiview controls geometry and proportions. A dense
control overlay guides feature coverage; the surface target controls quality
and topology presentation rather than independent dimensions.

Preferred inputs:

```text
input/multiview.png
input/front.png                 optional
input/side.png                  optional
input/rear.png                  optional
input/top.png                   optional
input/control_overlay.png
input/surface_target.png
```

Filenames are configured through project.json. The legacy Tesla filenames are
retained unchanged, including three `.png` names containing JPEG data.

Combined-sheet layout:

| Region | Contents |
| --- | --- |
| Top | Hero 3/4 view |
| Middle | FRONT, SIDE, REAR from left to right |
| Bottom | TOP view |

Separate orthographic images have priority over crops. Their dimensions and
framing must agree with the corresponding calibration record. Establish one
metric coordinate system: X longitudinal, Y lateral, Z up. Record origin,
ground, centerline, wheel centers, dimensional assumptions, uncertainty and any
rectification. Illustrative sheets are not automatically engineering drawings.
Do not silently force inconsistent views to agree.

Annotation convention: orange control points, blue visible splines, red inferred
or hidden curves, green datum/axes. HSV segmentation and eight-connected
components produce overlay_raw.json with centroids, bounds and sparse samples.
These are raw proposals, including false positives. They do not determine
semantic roles, validate dimensions or authorize surface construction.

Use semantic feature curves and independent surface boundaries. Do not use a
side silhouette plus top profile plus front section as a whole-body loft.
Presentation wire must follow actual control-mesh topology; arches/openings
must be geometry. Keep panels, glass, lamps and wheel assemblies logically
separate according to project bindings.
