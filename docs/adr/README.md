# VehicleRecon Studio decision records

Status: selected design baseline for architecture review, 2026-10-16. These
records document intended implementation boundaries; they do not claim shipped
Studio capabilities or operator approval of an implementation. Base core commit:
`a3592f33f3070f98aa8e6e1547da1bcb76c4eb15`.

| ADR | Decision |
|---|---|
| [0001](0001-studio-separated-from-core.md) | Studio is an authoring frontend separate from the reconstruction compiler |
| [0002](0002-canonical-project-json.md) | Existing canonical JSON family remains the only vehicle source of truth |
| [0003](0003-browser-and-localhost-backend.md) | Browser + authenticated loopback Python backend, REST + SSE |
| [0004](0004-threejs-preview-blender-authority.md) | Three.js feedback; Blender final geometry authority |
| [0005](0005-cv-results-are-proposals.md) | Optional CV outputs remain proposals until explicit acceptance |
| [0006](0006-observations-and-world-geometry.md) | Source observations and shared world geometry are separate |
| [0007](0007-source-inconsistency-first-class.md) | Source inconsistency is a first-class authoring result |
| [0008](0008-cancellation-job-outcome-conflict.md) | Proposed: resolve v0.1A cancellation outcome conflict; implementation stopped |

Technology comparisons are in [architecture](../studio_architecture.md).
Dependent implementation gates are in [roadmap](../studio_roadmap.md). Amend
typos in place; substantive reversals require a new ADR referencing the
superseded decision and its migration/regression consequences.
