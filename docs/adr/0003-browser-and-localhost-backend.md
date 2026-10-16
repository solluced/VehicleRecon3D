# ADR 0003 — Browser UI with localhost backend

Status: selected architecture baseline for review; implementation pending.

## Context

Interactive image editing belongs in the browser, while project I/O, Python
validation and Blender subprocesses need a local native service. The service
handles sensitive local files and process launch, even on one operator's machine.

## Decision

Use a bundled React/TypeScript browser client with an optional Python/FastAPI
backend, launched by the future `vehicle-recon studio`. Bind only authenticated
loopback on `127.0.0.1`, with same-origin assets/API and exact Host/Origin checks.
Use revisioned REST commands and one multiplexed SSE notification/log stream per
tab. Generate client contracts from OpenAPI/canonical schemas. Browser launch
uses a one-time bootstrap fragment and an HttpOnly session; no secrets in URLs
served as image/event resources.

## Alternatives

Browser filesystem APIs alone cannot safely own the existing compiler/runtime
workflow across supported browsers. A remote service expands the trust boundary.
WebSocket is unnecessary for initial request/event traffic. Electron/Tauri add
packaging obligations before they are justified. They are deferred, not initial
requirements. REST handles preview batches; SSE is not a pointer-motion channel.

## Consequences and verification

The backend needs path allowlists, schema validation, CSRF/session controls,
locking/recovery and serialized managed jobs. It must not expose a generic shell
or file browser. CLI remains standalone. Verify origin/traversal/concurrency
cases, reconnect/resync behavior and cancellation before writable release.

See [API](../studio_backend_api.md) and [security](../studio_security.md).
