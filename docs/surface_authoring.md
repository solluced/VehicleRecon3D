# Bounded surface authoring

Studio v0.5 authors `generated/surface_graph.json` through the shared
`AuthoringSession`. The graph is the canonical input to the existing bounded
operation evaluator. Three.js displays core samples; Blender remains authoritative
for production topology, modifiers, geometry audit and export.

## Contracts and drafts

New graphs use surface graph schema version 2. Existing v1 graphs and the accepted
Tesla fixture remain unchanged. Studio does not silently migrate an existing graph.
A node has a stable semantic ID, an existing operation ID, typed parameters,
explicit dependency IDs, per-input reversal and an explicit `draft` boolean.
Patches reference sample nodes by ID, independently of list order or resolution.
Name, semantic role and material role are metadata; display colors are not materials.

Draft nodes may omit required inputs. Supplied inputs must still satisfy their
operation schema; unknown references, cycles, unsupported operations, incompatible
dimensions, invalid sampling schedules and nonfinite values cannot be committed.
The UI may retain an invalid assignment transiently, clearly marked UNSAVED INVALID
DRAFT. Validation examines it without writing canonical files. Discard or correct
the assignment before execution. An incomplete canonical graph cannot execute.

All commands use revision preconditions, shared project locking, schema and semantic
checks, atomic multi-file commits and exact-byte undo/redo. Surface mutations seed
the existing `surfaces` dependency invalidation and downstream geometry/export
stages. Source/cage edits continue to invalidate reviews through core rules.

## Trusted operations

`GET /api/v1/surface-operations` exposes the exact trusted registry: `polyline`,
`chord_hermite`, `shape_preserving_hermite`, `bezier_rail_range`, `curve_sample`,
`lerp`, `offset`, `coons`, `cubic_boundary_roll`, `arch_annulus`, `ribbon`,
`bilinear_patch`, `boundary_stitch`. Metadata includes version, parameter schema,
required/optional inputs, output dimensions and preview/topology capabilities.
The UI builds its palette and parameter editors from this metadata. There are no
expression, Python, script, URL, plugin-import or arbitrary execution nodes.

The existing pure core math evaluates callable curves, points and surfaces.
`boundary_stitch` returns a discrete mesh rather than a callable surface and is
capability-disabled for authoring preview. Curve-derived `lerp` produces a surface;
point-derived `lerp` produces a point. `offset` preserves curve/point dimensionality.

Coons assigns bottom/top in increasing U and left/right in increasing V. Each
boundary has explicit forward/reverse direction. Corner reports show the expected
and actual coordinates, gap in metres, tolerance and individual PASS/FAIL. The
existing evaluator rejects disagreement; Studio never silently snaps corners.
Arch/fender authoring uses the same generic `arch_annulus`, `cubic_boundary_roll`,
`ribbon` and `offset` parameters, with no vehicle-specific implementation.

## Capabilities and deliberate limits

* Cage rail picking uses existing `bezier_rail_range`: VECTOR handles, noncyclic,
  strictly increasing X. Core converts VECTOR handles to the same straight Bezier
  controls as Blender. AUTO handles and other curve domains require Blender;
  they are not approximated as executable boundaries.
* Derived curves are sampled in core and can be picked in Three.js. The current
  trusted operation set has no generic extraction of an arbitrary previous patch
  edge. This capability is disabled with its reason in the catalog. Shared curve
  nodes and declared adjacency remain available; no new operation is invented.
* Support rows are existing explicit U/V sampling schedules. Add/remove a sampling
  position; independent strength/offset semantics are not present and are not
  simulated. Roll/arch control scales and ribbon offsets remain operation parameters.
* Symmetry uses the existing core-owned Y=0 mirror setting, including reversed
  mirrored winding and normals in the coarse mesh. The semantic counterpart is
  `<patch-id>.mirror`; it has no independent edited coordinate store. Other mirror
  planes and arbitrary mirror-source graphs are not offered.
* Material roles describe body paint, glass, trim, tire, light, interior or generic
  downstream intent. Studio does not author final shaders.
* Coarse projection is not offered as formal silhouette proof. Stage 07 and final
  Blender validation remain separate. Self-intersection certification is deferred
  to the Blender geometry audit; preview never claims it passed.

## Gates and quality

Both source and cage reviews must be current and ACCEPTED before evaluation,
sampled mesh generation or preview certification. Core checks these on every
request, even when returning cached functions/meshes. A stale Workspace cannot
evaluate a v2 graph directly. The pipeline's existing headless SURFACES gate and
the direct Blender surface builder also enforce acceptance. A new draft may be
authored before acceptance without producing a mesh.

The independent synthetic fixture contains two adjacent analytical planes with
current source/cage reviews. It is not a vehicle model and contains no Tesla/Mark II
coordinates. Mark II stays read-only and BLOCKED BY SOURCE/CAGE ACCEPTANCE.

Preview returns revision, graph hash, implementation identity, operation, patch ID
and resolution. Every display says COARSE AUTHORING PREVIEW / preview topology.
Wireframe uses actual indexed mesh edges. Face normals come from mesh triangles;
sample normals come from core surface derivatives. Degenerate/duplicate vertices,
zero-area triangles, nonfinite results, extreme aspect ratio, invalid sampling and
winding against the declared normal fail the preview. Failed output is never
certified current. A changed revision or external conflict visibly marks old output
STALE; generating again requires current reviews.

Adjacency comes from explicit canonical declarations or shared boundary node IDs,
never spatial proximity alone. Reports expose maximum/RMS G0 gaps, tolerance and
sampled normal-angle compatibility. These are G1-like diagnostics; no strict G1 or
G2 guarantee is made. Color heatmaps accompany numeric values and selectable patch
pairs. A failed connection cannot be hidden by an average across other connections.

## Cache and transport

Dependency keys include operation/version-bearing implementation source identity,
canonical node inputs/parameters/orientation, dependency keys and cage/calibration
identity. Unchanged nodes and patch meshes are reused; editing one node recomputes
that node and its downstream consumers. A cage/calibration change invalidates the
full preview. Caches are disposable and never establish acceptance.

Core function LRU is bounded to 256 entries; sampled mesh LRU to 64 entries/16 MiB
of serialized payload. Python object overhead is measured separately as process
RSS. Studio history retains at most 100 edges/32 MiB of canonical byte payload.
Existing CV and transport replay limits remain in force.

Typed routes inspect the graph, registry, validation and preview. Existing
`transactions` carries surface commands, not arbitrary patches or code. Events are
`surface_graph_changed`, `surface_preview_stale`, `surface_preview_ready` and
`surface_validation_changed`; no pointer-motion stream is added.
