# Studio local security and trust boundaries

v0.2 preserves these controls for source/world/correspondence commands and
project-scoped preview APIs. Fit proposals are typed, time/count bounded and
fenced to project/tab/revision; reviews require inspected subject identity.
Three.js receives core JSON samples, with no unrestricted model/URL/file loading.
Bounded history/replay retention is documented in [development](studio_development.md).

v0.1B implementation: the manual editor implements and tests loopback binding,
exact Host/Origin, bootstrap/session/CSRF, safe opaque registries, bounded image
imports, core locks/revisions/transactions, leases and SSE replay. The original
threat model below remains the design input for later features; provider/build
and artifact-serving controls are not claimed as new v0.1B endpoints. See
[development/security details](studio_development.md) and the phase test evidence.

Historical design baseline: the threat model below includes later provider/build
controls. The implementation updates above identify the protections shipped in
the current localhost service. See [API](studio_backend_api.md) and
[transaction guarantees](studio_data_flow.md#revisioned-save-and-crash-consistency).

## Assets, actors and scope

Protect original images, canonical authored geometry, local files outside the
project, validation/review identities, process execution and availability. Trust
the installed application/core and operator-configured startup roots/executables.
Treat references, filenames, project JSON, model outputs, browser inputs and logs
as untrusted data. A project directory is not permission to run code found there.

Relevant threats include a malicious website reaching loopback, DNS rebinding,
CSRF, imported-path traversal, symlink/junction escapes, stale concurrent writes,
active content in artifacts, oversized images/contours, corrupted manifests and
an external editor racing a build. A malicious process with the same OS account
can often read/change the same files; localhost authentication and advisory locks
are not an OS sandbox against that process. They still prevent accidental and
cross-origin access. Remote hosting, untrusted plugins and multi-user accounts
need a separate security design; LAN mode is not an initial option.

## Network, session and browser boundary

Bind explicitly to `127.0.0.1`; IPv6 loopback may be a separately validated future
origin. Never bind `0.0.0.0` or `::`, and reject startup requests to expose a remote
interface in the initial product. Use one ephemeral port and an exact allowed
Host/Origin tuple. A resolved loopback address alone is insufficient: reject
unexpected Host values to mitigate DNS rebinding. Serve API and bundled UI on
the same origin with no permissive CORS policy.

The launcher creates a cryptographically random one-time bootstrap secret in a
URL fragment, not a query string or printed access URL containing the secret.
Frontend reads it once, exchanges it via an authenticated Origin-checked POST,
clears it from history, and establishes an HttpOnly, host-only, SameSite=Strict
session cookie. Use Secure when TLS is configured; plain HTTP loopback cannot
be assumed to support identical Secure-cookie behavior in every browser.
Issue a session-bound CSRF token for all mutations and verify the expected
Origin/content type. Apply authentication to reads, event streams, images,
schemas, logs and artifacts; only safe static boot assets can be unauthenticated.

GET endpoints are side-effect free. Browser SSE uses the session cookie; no
tokens in event/image/artifact URLs, console output, referrers or process logs.
Reject cross-site fetch metadata where present and validate Origin when sent;
an absent Origin on a normal same-origin image/GET does not bypass session or
Host checks. Rotate secrets per service launch; bootstrap tokens expire and are
single-use. Failed authentication never reveals a filesystem inventory.

Protect or disable framework-generated OpenAPI/interactive docs endpoints too.
Redact bootstrap/session/CSRF headers, cookies and credentials from all access
and diagnostic logs; production responses never enable a debug traceback page.

Bundle frontend/CV runtime assets locally and use a restrictive Content Security
Policy: self scripts/styles/workers, no unsafe-eval, no remote scripts, no
arbitrary frame ancestors, and object/base restrictions. Provider-specific WASM
or worker policies must be narrowly documented/tested rather than enabled by
universal unsafe directives. Opt into cross-origin isolation only when required
and tested for a provider; manual editing and baseline CV remain usable without
WASM multi-threading or WebGPU. No default telemetry or remote inference/upload.

## Filesystem and artifact boundary

Allowed roots are trusted startup configuration. Browser operations use opaque
root/project/reference/artifact IDs, never absolute paths, directory browsing or
arbitrary file reads. Project creation derives safe child directory names, checks
Windows reserved names/case aliases and refuses to overwrite an existing project.
Existing projects are discovered only within configured roots and index policy;
do not recursively expose `.git`, credentials, attachments or unrelated folders.

Reuse `Project.path` restrictions: project-relative POSIX paths, no drive/UNC,
backslash, parent traversal, colon or resolved escape. Extend the I/O boundary
for OS-specific file operations: resolve real paths and reject symlink/junction
escapes, validate containment before create/replace, and recheck under the lock.
Use safe directory/file handles or equivalent no-follow checks where possible
to reduce check/use races. Resolve case and path aliases consistently; a source
must not alias an output, lock file, transaction backup or another protected file.

Uploads preserve byte content under service-generated names and hashes; supplied
names are display metadata. Decode verified supported image formats with file,
dimension and memory limits before accepting them. Initial proposed ceilings:
64 MiB encoded per image, 64 megapixels decoded, bounded concurrent decode and
total workspace quota. They are resource controls to benchmark, not core source
accuracy limits. Preserve legacy extension/content differences by detecting file
signatures. Do not import active SVG/HTML as a trusted inference bitmap or execute
embedded metadata. Record any display orientation separately from source pixels.

Serve only registered images/artifacts whose identities pass the manifest/path
checks. Verify size/hash when making them available. Use correct MIME types and
`nosniff`; user names and reports are escaped text. Canonical JSON and log text
must not become script/HTML. A generated viewer HTML is active content: embed it
only in a sandboxed frame without same-origin privileges, or offer an explicit
download. Prefer loading the verified GLB into Studio's own trusted viewer.
Validate GLB/accessor bounds and apply model-resource limits before browser load.
No artifact registry entry may bypass allowed-root containment.

## Authoring writes, review and concurrency

Every committed write is schema-validated under its declared supported version
and checked by core semantics: finite numbers, bounds/cardinality, role bindings,
safe references, invertibility, graph operations/cycles, limits and immutable
datums. An incomplete wizard draft needs its own planned core draft contract;
do not bypass full validation with `check=False` and call it a successful save.
Newer unsupported schemas are read-only until an explicit supported migration.

Use revision preconditions, idempotency keys, one editor lease, shared core OS
locks and journalled multi-file transactions. A lease is not proof no CLI writer
exists; all mutating CLI/backend entry points must adopt the same lock. File
watching is advisory; rehash immediately before commit and at build boundaries.
Never overwrite an unexpected external change during save, restore or recovery.
Restore/migrate are validated transactions with diff/backup, not recursive moves
or broad deletion of arbitrary paths.

Source/CV proposals and rejected candidates cannot set accepted geometry or
review fields through a general property setter. Specialized acceptance services
bind explicit decisions to actual evidence and current hashes. Confidence,
layer visibility and preview toggles never lower tolerances or unlock a source
gate. The standard final review remains explicit; stale/missing review blocks
the same operations in CLI and Studio. Mark II's rejection/limits stay unchanged.

## Process and provider boundary

The backend exposes only allowlisted core stage/operation IDs and bounded typed
parameters. Invoke trusted Python/core and Blender executables with argument
arrays and no shell interpolation. Runtime paths come from trusted startup
configuration/discovery, never project JSON or web requests. No arbitrary shell,
eval/exec, dynamic module import, script upload, Blender expression, environment
assignment or project-installed plugin endpoint is available.

The installed core's own trusted Blender entry code is the only build worker
code launched. Keep factory-startup behavior; do not enable Python auto-run from
imported `.blend` files. Imported projects do not select startup scripts/addons.
Manage subprocess groups/Windows Job Objects so cancel shuts down owned workers
without killing unrelated Blender or browser sessions. Bound CPU/GPU work,
request sizes, queued jobs, execution time and log volume. Serialize backend
builds initially. Release locks only after the worker exits or is safely fenced.

CV providers execute in bounded optional workers and return validated proposal
envelopes. Only installed, operator-selected providers/models run. Downloads,
license acceptance or remote inference require separate explicit product intent;
no image is sent off-device implicitly. Verify configured model identity/checksum,
pin runtime/model compatibility and record model provenance. Model confidence
cannot override a failed geometric check. Browser/WebGPU absence must fall back
to an available local provider or manual authoring.

## Required security verification before writable release

| Attack/failure | Required observable result |
|---|---|
| Cross-origin POST/SSE, hostile Host, reused bootstrap token | Rejected without project disclosure or side effects |
| `../`, encoded traversal, drive/UNC, mixed separators, junction/case alias | Rejected under both API and core paths |
| Symlink/junction swapped between checks | No write/read outside root; transaction aborts safely |
| Oversized image, decompression bomb, huge contour/GLB, endless logs | Budget rejection/cancellation; authored data intact |
| Filename/log/report containing HTML | Displayed as inert text |
| Forged candidate accept, review hash or hidden failed layer | Cannot activate/accept without valid current evidence |
| Two tabs, CLI race, Git checkout, external edit during build | Lock/conflict/stale-run outcome; no silent overwrite/current export |
| Crash after any transaction replace | Detect mixed revision, recover old/new matching state or request conflict resolution |
| Cancel/restart with Blender child alive | Owned process reconciled/fenced before unlock; no false successful result |
| Project data requests code or a different executable | Rejected; trusted allowlist only |

These tests accompany implementation, not this documentation-only phase. The
architecture has no security exception that would require exposing local files
or remote services merely to demonstrate the UI.
