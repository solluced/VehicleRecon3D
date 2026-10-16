# Studio implementation roadmap and architecture exit

Status: architecture baseline for review. This phase delivers documentation only,
on core base `a3592f3`; no production Studio code or optional prototype is added.
The command/API/packages described in these documents are planned capabilities.

v0.1A implementation update: the six core foundation dependencies below are now
implemented and tested; see [core authoring](core_authoring.md) and phase evidence
in `validation/studio_v0.1a/`. The design-phase text records the original baseline.
This does not start production FastAPI, React or Mark II reconstruction.

## Architecture decisions selected for review

Separate optional Studio workspace; React/TypeScript shell; Konva 2D adapter;
Three.js feedback/verified GLB; Python/FastAPI localhost backend; REST commands
and multiplexed SSE notifications; optional hybrid CV providers. Canonical data
remains the existing VehicleRecon JSON family. Core/Blender own reconstruction
and acceptance. The [ADR index](adr/README.md) records the boundaries and rejected
alternatives. No architecture approval by the operator is inferred from writing
the documents; this is the concrete reviewable baseline for the next phase.

## Foundation before writable Studio

Implement these as small generic core increments with independent tests and
regressions, not a Studio-specific reconstruction fork:

| Dependency | Required outcome / release gate |
|---|---|
| Versioned authoring contracts | Typed source observations/vectors/measurements, draft/readiness, shared landmark references and stable point identity; no new vehicle files/ontology owned solely by Studio |
| Version/migration service | Read v1 without modification, explicit backed-up migration to supported authoring family, unsupported future versions read-only |
| Shared authoring service | Typed commands, schema + semantic validation, projection/sampling and binding updates usable without a web server |
| Shared lock/transaction service | CLI/backend/review/build cooperation, revision preconditions, multi-file journal/recovery, external-change checks |
| Early acceptance gate | New authoring workflow enforces current source/cage reviews before surfaces in both CLI and Studio; source rejection is preserved |
| Event/job hooks | Optional generic observer, managed cancellation/log capture and pinned-input guards without web imports in core |

Sequence these dependencies to avoid building large UI infrastructure before
core contracts exist. Initial read-only discovery/viewing can precede them;
canonical writes cannot. Explicit tangent editing, advanced constraints and
Blender-accurate AUTO-handle sampling can arrive with their dependent tools,
provided those tools remain capability-disabled until supported.

Compatibility policy: the core continues to read/run existing v1 projects with
their documented gate coverage and unchanged Tesla behavior. A new v2 authoring
contract enforces its additional early reviews in **both** execution paths.
Studio opens legacy v1 projects read-only for the new authoring workflow until
explicit migration; it does not claim an old v1 cage-construction PASS certifies
semantic acceptance. No hidden project-name exemption or auto-PASS migration is
allowed. Migration carries evidence forward as historical material and requires
new review where the new contract needs it. Keep a v1 Tesla regression plus
independent consistent fixtures for the new gate/authoring contract.

Every core behavior/schema increment requires relevant unit/negative tests,
unchanged frozen fixtures and a full Tesla regression: SIDE 0.957230, TOP
0.936083, FRONT 0.931202, REAR 0.944724, existing documented geometry tolerances,
all pipeline gates, direct GLB verification and browser QA. Do not alter expected
metrics after a regression. Studio-only documentation/UI changes need focused
checks; they do not justify rerunning unrelated Blender work indefinitely.

## Incremental product releases

| Increment | Scope | Observable exit gate |
|---|---|---|
| Architecture, this phase | Seven design documents, seven ADRs, current-state gap/contract inventory, API prototypes | Required areas specified; docs/source links coherent; core, projects and evidence unchanged |
| Studio v0.1: manual authoring foundation | Project browser, optional install/launcher, schema settings, wizard/drafts, immutable image import/crops, pan/zoom, layers, points, source splines, command undo/autosave/watch conflicts | Manual project can be authored/reopened without JSON, CV or LLM; originals hash-identical; generic contracts/locking passed before writes |
| Studio v0.2: correspondence and consistency | Measurements/provenance, multi-view links, individual residuals, basic source rejection/heatmap, 2D/3D cage split and reference/cage review | Known conflicting fixture rejected before surfaces; one world move updates all views; no independent 2D-derived XYZ; all critical checks visible |
| Studio v0.3: annotation assistance | CVProvider registry, baseline local OpenCV edges/contours/wheel proposals, Smart Edge, Magic Select, simplification/fitting | Providers optional, failures harmless, proposals revision-bound and explicitly accepted; manual workflow remains complete |
| Studio v0.4: advanced reference reconciliation | Full anchor editor, mapping/derivative graphs, candidate comparison, magnitude/extrapolation and held-out evidence, optional browser ONNX provider | Rejected candidate never active; exact datum anchors; strict existing limits; Mark II-like scale 0.518–2.150 rejected visibly |
| Studio v0.5: bounded surface authoring | Patch/boundary assignment, operation palette, support rows, material/mirror, coarse core preview, supported quality inspectors | Source/cage gates enforced headlessly before surfaces; no arbitrary scripts; real boundary/topology checks; preview labelled correctly |
| Studio v0.6: production build orchestration | Full 14-stage panel, live logs/events, cancel/restart recovery, Blender builds, verified GLB reload | UI and CLI native results agree; same cache keys/output checks; no orphan worker or stale artifact promoted |
| Studio v0.7: review and export workflow | Final visual-review screen, supported exports, adapter capability/configuration boundary | Explicit hash-bound review; stale review blocks export; adapters reject missing requirements; no game-readiness claim from GLB alone |

This refines the suggested order by moving **basic** source conflict/rejection
into v0.2 and requiring the headless gate before surface UI ships. Full
rectification tooling remains v0.4. A small orchestration diagnostic may be built
early to test locks/events, but does not ship a bypass around source acceptance
or manual review while the polished Run page waits for v0.6.

No date estimates are invented. The next product increment should be scoped to
one measured end-to-end vertical slice, not a giant frontend assembled before
contract/performance review. Each coherent implementation milestone gets its
own commit; this architecture commit is separate from reconstruction changes.

## Verification plan by boundary

| Boundary | Required verification |
|---|---|
| Pure core | Schema versions, observation/world separation, stable binding on insert/delete/split/merge, exact projection/warp roundtrips, profile floors, graph validity and individual residuals |
| Storage | Revision conflicts, idempotent retries, immutable source hashes, crash injection after every multi-file replace, checkpoint/undo/recovery and Git/external edits |
| Processes | Concurrent CLI/Studio writers, queue ordering, cancellation before/during stages, backend restart, child fencing, input mutation during build |
| API/security | Origin/Host/session/CSRF, traversal/junction/case alias, bounded uploads/contours/GLB/logs, no arbitrary shell/file access |
| Browser | Pointer-anchored zoom, keyboard editing, layer locks, high-DPI coordinates, reversible drags, stale-preview suppression and context loss |
| Performance | Declared 4K/5,000-point/20-layer workload, p95 frame/pick/preview budgets, memory/worker cleanup; compare Konva against raw Canvas/WebGL only if measured limits fail |
| CV | Disabled/offline/provider-error paths, source/crop normalization, model provenance, empty/false-positive proposals, explicit acceptance and deterministic fallback |
| Integration | Same project/CLI builds, exact verified GLB loading, real mesh-edge topology, explicit review invalidation, source rejection before surface construction |

Run optional Studio tests in their own CI/install job. Core tests do not acquire
FastAPI/React/Konva/ONNX dependencies. Preserve existing core Blender/browser
integration jobs; they remain headless. No CV model download is needed for unit
CI; small deterministic provider fixtures test the proposal contract.

## Handoff coverage map

| Handoff sections | Primary specification |
|---|---|
| 0–3, 42–45 | [Architecture](studio_architecture.md): compiler/frontend boundary, package/technology choices, adapters/local deployment |
| 4–8 | [UI](studio_ui_spec.md): workflow layout, navigation, full layer/tool vocabulary |
| 9–12 | [UI](studio_ui_spec.md), [API](studio_backend_api.md): CVProvider, Smart Edge, vector fitting, semantic mapping |
| 13–18 | [Data flow](studio_data_flow.md), [UI](studio_ui_spec.md): shared identity, observations, residuals, consistency, candidates, immutable sources |
| 19–23 | [Data flow](studio_data_flow.md), [UI](studio_ui_spec.md): schema forms, canonical files, history, save/checkpoints, dirty state |
| 24–29 | [UI](studio_ui_spec.md), [API](studio_backend_api.md): preview/split, bounded graph, quality modes, stage/result/build contracts |
| 30–34 | [Architecture](studio_architecture.md), [API](studio_backend_api.md), [Security](studio_security.md): transport, service, advanced settings, optional assistance |
| 35–41 | [Product](studio_product_spec.md), [UI](studio_ui_spec.md): Mark II/source rejection, wizard/import/measurements, validation and explicit review |
| 46–49 | [UI](studio_ui_spec.md), [Data flow](studio_data_flow.md), [API](studio_backend_api.md): budgets, file watching, versioning/migration and operations |
| 50–55 | This roadmap and ADRs: documentation-only phase, no optional spike, phased implementation, prohibitions, separate Git milestone and final report |

## Phase exit and preserved state

Required files: `studio_architecture.md`, `studio_product_spec.md`,
`studio_ui_spec.md`, `studio_backend_api.md`, `studio_data_flow.md`,
`studio_security.md`, `studio_roadmap.md`, plus ADRs 0001–0007. All are documentation;
contract fragments are illustrative and no new runtime formats are activated.

The optional spike is omitted: architecture and executable contracts should be
reviewed before a canvas experiment; no prototype serialization is needed to
establish this baseline. No production frontend or schema change is expected yet.

Mark II remains BLOCKED, active calibration unchanged, cage FAIL,
surfaces/details NOT STARTED. Its reference inconsistency evidence remains
byte-identical to the base commit. Tesla/project/core files are untouched.
There are no missing inputs blocking this design deliverable. The listed generic
core extensions are implementation prerequisites, not completed features or
reasons to resume the invalid Mark II reconstruction.
