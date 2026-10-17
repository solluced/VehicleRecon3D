# ADR 0005 — CV results are proposals

Status: accepted architecture; local OpenCV baseline implemented in Studio v0.3.

## Context

Segmentation, wheels, edges, contours and semantic suggestions can reduce
repetitive annotation. They can also identify reflections or body-kit features
incorrectly. A provider/model must not become geometry or dimension authority.

## Decision

Use optional CVProvider adapters with declared capabilities and a common
source/crop/revision/provenance envelope. Start with backend OpenCV for baseline
image operations. Allow capability-detected browser ONNX/WASM/WebGPU or other
installed providers later. No mandatory model family, provider or LLM exists.

Every result is a proposal. The operator inspects/corrects and explicitly accepts
it into canonical source observations/traces through an undoable transaction.
Rejected/stale proposals cannot alter active geometry or acceptance. Confidence
is displayed as qualified provider information, not a substitute for residual
tolerances. Source bytes remain unchanged.

## Alternatives

Direct CV-to-surface activation, hard-coded model services, automatic review
PASS and mandatory cloud inference would hide failure and break the manual/offline
workflow. These alternatives are not selected. Smart Edge may use provider
signals while always permitting manual seeds/segments.

## Consequences and verification

Provider absence, no GPU, model errors and low-confidence results leave manual
tools fully usable. Verify coordinates/provenance across providers, explicit
accept/reject, cache freshness and undo. Downloads/licensing/remote processing
require separate explicit product design; nothing sends images off-device by
default.

See [CVProvider contract](../studio_backend_api.md#cvprovider-interface-prototype).
The implemented optional provider, job and proposal contracts are documented in
[cv_provider.md](../cv_provider.md); user workflows are in the
[v0.3 manual](../studio_user_manual_v0.3.md).
