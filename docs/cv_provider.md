# Local annotation providers

Studio v0.3 introduces optional source-pixel assistance. The headless core has
no OpenCV dependency. Install `studio/backend[cv]` to enable the pinned
`opencv-python-headless==4.14.0.94` provider, or launch with `--disable-cv`.
Missing/disabled providers are explicitly unavailable; requests never silently
switch provider, download a model or send imagery off-device.

## Ownership and contracts

`vehiclerecon_studio.cv.providers.CVProvider` is a trusted installed adapter with
metadata and `run(capability, image_bytes, parameters, context)`. ProviderRegistry
registers code-owned instances, discovers capabilities and rejects unknown or
unavailable identities. Browser/project strings cannot select a Python module,
filesystem path, URL, shell command or model executable. OpenCV supports edges,
connected contours, directed Smart Edge, GrabCut regions and circle candidates.
It makes no claim of semantic vehicle understanding; proposals begin UNKNOWN.

`schemas/cv_request.schema.json`, `cv_edit.schema.json` and `cv_proposal.schema.json`
define strict requests, pixel geometry and the proposal envelope. A proposal
contains source/reference/crop identity, exact canonical revision, provider/version,
parameters, input hash, provenance, addressable components and status. Dense
source samples remain available alongside reduced points, cubic knots and fit
evidence. Raster diagnostics are ordinary project-scoped PNGs with explicit
source-pixel bounds; they are never canonical geometry.

CVService keeps proposals transient and byte/count bounded. Current source,
framing, observation context or review changes invalidate active proposals.
Provider-parameter changes explicitly invalidate/recreate the selected proposal.
Proposal edits advance a separate proposal revision; stale edit/accept tokens
conflict. ACCEPT alone creates source observations through existing core typed
commands, validation, revision locks, journalling and history. Batch selection
supports partial acceptance; unselected components become stale when canonical
context changes. REJECT and proposal edits leave canonical bytes/reviews alone.
Acceptance never moves world landmarks or axles. Geometry survives cache eviction
because it is copied into canonical observations, with self-contained provenance.
Accepted evidence stays INFERRED unless the operator explicitly confirms pixels.

## Local execution and resource bounds

One dedicated worker thread serializes OpenCV work, with OpenCV CPU threads set
to one, OpenCL disabled and RNG seed zero. FastAPI handles submission/progress/
cancellation independently of the native work. Four queued/running jobs and
64 MiB pending encoded sources are allowed; source images are limited to
16 megapixels and mask/wheel ROIs to 4,194,304 pixels. Smart Edge searches at most
262,144 local pixels / 80,000 expanded A* nodes. Edge tiles and decoded images are
cached rather than reprocessing the full 4K image on pointer motion.

Cancellation is cooperative, checked during search, between GrabCut iterations
and before publication. A native OpenCV call must return before cancellation
finishes; the UI must not call CANCELLING a completed cancellation. Jobs are
revision-pinned and old results are fenced before publication. Failure, empty
output, cancellation and allocation errors cannot write canonical data. Manual
authoring does not depend on the worker. Idle caches are disposable; no CV cache
files are created inside protected vehicle projects.

Retention: 64 proposals / 24 MiB; 32 deterministic results / 16 MiB; 64 decoded
image/edge entries / 64 MiB; 128 small job records. Budgets count retained data
bytes, not Python/native allocator RSS. Rejected/stale proposals participate in
eviction. Result keys include provider version, capability, parameters, exact
image hash, crop identity/bounds and source view. A cache hit gets a new envelope
pinned to the current observation context, never a reused stale acceptance.

## Geometry and score limits

Smart Edge uses local Canny/gradient strength, pointer-trajectory proximity and
direction cost in a bounded deterministic A* search. It needs at least two
directed source points; one click cannot trace a complete vehicle. GrabCut uses
a user ROI and explicit foreground/background strokes. Circle scores describe
geometric circularity; they are not calibrated probabilities of a wheel.

Pure `authoring.contours` performs RDP interval simplification and optional cubic
fitting without OpenCV. It preserves endpoints and requested important corners.
The largest original interval distance to its chord plus the Bezier control-hull
distance to that same finite chord bounds the continuous bidirectional error.
This follows from convexity and endpoint-connected paths covering the chord's
projection. Point limits never override the error bound: an impossible budget
returns an explicit error. Max/RMS sample deviation and the continuous upper bound
are reported separately; adaptive flattening has a 0.025 px display-measure error.

Primary references: [Canny / circle detection](https://docs.opencv.org/4.13.0/dd/d1a/group__imgproc__feature.html),
[GrabCut](https://docs.opencv.org/4.x/d8/d83/tutorial_py_grabcut.html),
[pinned OpenCV package](https://pypi.org/project/opencv-python-headless/4.14.0.94/).
