# v0.1A core authoring validation

This evidence accompanies the implementation after explicit acceptance of
ADR-0008. It does not certify a new vehicle asset or start Studio's HTTP/UI work.
`report.json` records the overall result and protected-data checks. `pytest.xml`
records the complete final test run, including real Blender cancellation.

Tesla was rebuilt with all 14 native stages and `--no-cache` in
`build/studio-v01a-tesla-cold/`, initially containing only published v1
`project.json`, `input/`, `generated/` and the existing explicit final review.
No Blender checkpoints, exported model or proof images seeded that run.
The eight regenerated review proofs were byte-identical to the accepted proofs;
no new reviewer decision or relaxed threshold was needed.

The `tesla/` reports are copied from that isolated run. Final IoUs are exactly
SIDE .957230, TOP .936083, FRONT .931202, REAR .944724. The control comparison
uses the frozen delivered Blender file read-only: topology/structure pass,
cage controls/handles are exact, maximum control coordinate difference is
1.1920928955078125e-7 m against a 1e-5 m tolerance.

`glb_comparison.json` compares decoded fresh/published GLB positions, normals,
indices and nodes exactly. UVs differ by at most one float32 ULP
(5.960464477539063e-8); this is reported rather than claiming byte-identical GLBs.
GLB-to-evaluated-Blender validation, exact viewer embedding, real desktop/mobile
browser controls and delivery manifest integrity pass independently.

`managed_worker.json` records successful isolated real Blender calibration,
hash-checked publication and subsequent verified cache reuse under the final
implementation identity. Unit/integration tests separately verify queued,
pre-first, between-stage, active Python and real Blender cancellation, failure
precedence, descendant fencing, finalized no-ops and promotion suppression.

Mark II is not migrated or reconstructed. Protected source/calibration/cage/
Blender hashes match its existing reconciliation report; the extreme inactive
candidate remains rejected. Published vehicle trees and both frozen Tesla
fixtures have no tracked changes against architecture base `58f13e8`.

Large Blender files/browser screenshots and run-scoped execution logs remain in
the ignored local build workspaces. The reports retain their original artifact
hashes/relative paths; copying them here is diagnostic evidence, not a relocated
delivery manifest. The final v2-only settings validation refinement does not
change v1 build behavior; the final full suite includes it.
