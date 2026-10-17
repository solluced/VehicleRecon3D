import { useEffect, useRef, useState } from "react";
import type { EditorClient } from "./api";
import type { AuthoringCommand, Schema, Snapshot } from "./types";
import { SchemaField } from "./Forms";
import { SurfacePreview3D } from "./SurfacePreview3D";
import {
  previewCurrent,
  type SurfaceContext,
  type SurfaceCatalog,
  type SurfacePreview,
  type SurfaceGraph,
  type Adjacency,
  type Validation,
} from "./surface-types";
import "./surface.css";
const uid = (prefix: string) =>
  prefix + "." + crypto.randomUUID().replaceAll("-", "");
export function SurfaceWorkspace({
  snapshot,
  client,
}: {
  snapshot: Snapshot;
  client: EditorClient;
}) {
  const [context, setContext] = useState<SurfaceContext | null>(null),
    [catalog, setCatalog] = useState<SurfaceCatalog | null>(null),
    [selected, setSelected] = useState(""),
    [nodeID, setNodeID] = useState(""),
    [preview, setPreview] = useState<SurfacePreview | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [picked, setPicked] = useState(""),
    [wire, setWire] = useState(false),
    [normals, setNormals] = useState("off"),
    [color, setColor] = useState("semantic"),
    [quality, setQuality] = useState("low"),
    [name, setName] = useState("New bounded patch"),
    [role, setRole] = useState("panel"),
    [operation, setOperation] = useState("coons"),
    [validation, setValidation] = useState<Validation[] | null>(null),
    [transient, setTransient] = useState<SurfaceGraph | null>(null);
  const latest = useRef(snapshot),
    seq = useRef(0);
  latest.current = snapshot;
  const base = "/projects/" + snapshot.id;
  useEffect(() => {
    void client.api
      .call<SurfaceCatalog>("/surface-operations")
      .then(setCatalog)
      .catch((e) => setError(String(e)));
  }, [client]);
  useEffect(() => {
    const token = ++seq.current;
    void client.api
      .call<SurfaceContext>(base + "/surfaces")
      .then((c) => {
        if (seq.current === token) {
          setContext(c);
          setValidation(null);
        }
      })
      .catch((e) => setError(String(e)));
    return () => {
      seq.current++;
    };
  }, [snapshot.id, snapshot.revision, client, base]);
  const graph = transient || context?.graph,
    patch = graph?.patches.find((p) => p.id === selected),
    node = graph?.nodes.find((n) => n.id === (nodeID || patch?.sample)),
    metadata = catalog?.operations.find((o) => o.id === node?.op),
    inputs = metadata
      ? [...metadata.required_inputs, ...metadata.optional_inputs]
      : [];
  const writable =
    client.writable && !busy && context?.revision === snapshot.revision;
  async function commands(values: Record<string, unknown>[]) {
    setError("");
    setValidation(null);
    const okay = await client.commands(values as unknown as AuthoringCommand[]);
    return okay;
  }
  function selectPatch(id: string) {
    setSelected(id);
    setNodeID("");
  }
  async function create(asPatch: boolean) {
    const node_id = uid("sample"),
      patch_id = uid("patch");
    if (
      await commands([
        asPatch
          ? {
              type: "AddSurfacePatch",
              node_id,
              patch_id,
              name,
              semantic_role: role,
              op: operation,
            }
          : { type: "AddSurfaceNode", node_id, op: operation },
      ])
    ) {
      setSelected(asPatch ? patch_id : "");
      setNodeID(asPatch ? "" : node_id);
    }
  }
  async function evaluate() {
    if (!context) return;
    setBusy(true);
    setError("");
    const rev = snapshot.revision;
    try {
      const result = await client.api.post<SurfacePreview>(
        base + "/surface-preview",
        {
          expected_revision: rev,
          quality,
          ...(transient ? { graph: transient } : {}),
        },
      );
      if (latest.current.revision === rev) {
        setPreview(result);
        setValidation(result.validation);
      }
    } catch (e) {
      setError(String(e));
      if (transient) setPreview(null);
    } finally {
      setBusy(false);
    }
  }
  async function assign(boundary: string, source: string) {
    if (!node || !context || !source) return;
    if (source.startsWith("cage:")) {
      const id = source.slice(5),
        c = context.cage_boundaries.find((c) => c.id === id);
      if (!c) return;
      const derived = uid("rail");
      await commands([
        { type: "AddSurfaceNode", node_id: derived, op: "bezier_rail_range" },
        {
          type: "SetSurfaceParameter",
          node_id: derived,
          parameter: "curve",
          value: id,
        },
        {
          type: "SetSurfaceParameter",
          node_id: derived,
          parameter: "x_range",
          value: c.x_range,
        },
        { type: "SetSurfaceDraft", node_id: derived, draft: false },
        {
          type: "SetSurfaceBoundary",
          node_id: node.id,
          boundary,
          source: derived,
        },
      ]);
    } else {
      const candidate = structuredClone(context.graph!);
      const proposed = candidate.nodes.find((n) => n.id === node.id)!;
      proposed.parameters[boundary] = source;
      proposed.dependencies = Array.from(
        new Set(
          inputs
            .filter((k) => k in proposed.parameters)
            .map((k) => String(proposed.parameters[k])),
        ),
      ).sort();
      const r = await client.api.post<{ validation: Validation[] }>(
        base + "/surface-validation",
        { expected_revision: snapshot.revision, graph: candidate },
      );
      if (r.validation.some((v) => v.status === "FAIL")) {
        setTransient(candidate);
        setValidation(r.validation);
        setPreview(null);
        return;
      }
      setTransient(null);
      await commands([
        { type: "SetSurfaceBoundary", node_id: node.id, boundary, source },
      ]);
    }
  }
  async function validateDraft() {
    if (!graph) return;
    setError("");
    const r = await client.api.post<{ validation: Validation[] }>(
      base + "/surface-validation",
      { expected_revision: snapshot.revision, graph },
    );
    setValidation(r.validation);
  }
  if (!context || !catalog)
    return <p>Loading core surface contracts… {error}</p>;
  const current =
      previewCurrent(preview, snapshot.revision) && !client.state.conflict,
    stale =
      !!preview &&
      (preview.revision !== snapshot.revision || client.state.conflict);
  return (
    <main className="surface-workspace" aria-label="Surfaces workspace">
      <header className="surface-header">
        <div>
          <h2>Bounded surfaces</h2>
          <strong>{context.gate}</strong>
        </div>
        <div className="surface-controls">
          <button
            aria-label="Undo"
            disabled={!writable || !snapshot.history?.undo}
            onClick={() => void client.run("undo", {})}
          >
            Undo
          </button>
          <button
            aria-label="Redo"
            disabled={!writable || !snapshot.history?.redo}
            onClick={() => void client.run("redo", {})}
          >
            Redo
          </button>
          <label>
            Preview resolution
            <select
              aria-label="Preview resolution"
              value={quality}
              onChange={(e) => setQuality(e.target.value)}
            >
              <option value="low">Low · up to 8 × 8</option>
              <option value="medium">Medium · up to 16 × 16</option>
            </select>
          </label>
          <button
            disabled={
              !context.evaluation_allowed ||
              busy ||
              context.revision !== snapshot.revision
            }
            onClick={() => void evaluate()}
          >
            Generate coarse preview
          </button>
          <span role="status" data-testid="surface-preview-status">
            {stale
              ? "STALE — regenerate after current reviews"
              : transient
                ? "BLOCKED · INVALID DRAFT"
                : current
                  ? "CURRENT · " + preview?.status
                  : preview
                    ? "UNCERTIFIED · " + preview.status
                    : "NOT GENERATED"}
          </span>
        </div>
      </header>
      <p className="surface-notice">
        COARSE AUTHORING PREVIEW · preview topology · Blender owns final
        geometry. Self-intersection audit deferred to Blender.
      </p>
      {error && <p role="alert">{error}</p>}
      {transient && (
        <p role="alert">
          UNSAVED INVALID DRAFT — evaluation blocked; canonical graph unchanged.{" "}
          <button
            onClick={() => {
              setTransient(null);
              setValidation(null);
              setError("");
            }}
          >
            Discard invalid draft
          </button>
        </p>
      )}
      <div className="surface-grid">
        <aside>
          <h3>Patches</h3>
          <div role="list" aria-label="Surface patches">
            {graph?.patches.map((p) => (
              <button
                role="listitem"
                aria-pressed={p.id === selected}
                key={p.id}
                onClick={() => selectPatch(p.id)}
              >
                {p.name || p.id}
                <small>
                  {p.id} ·{" "}
                  {graph.nodes.find((n) => n.id === p.sample)?.draft
                    ? "DRAFT / INCOMPLETE"
                    : "READY FOR EVALUATION"}
                </small>
              </button>
            ))}
          </div>
          <h3>Operation palette · core</h3>
          <label>
            Operation
            <select
              aria-label="Surface operation palette"
              value={operation}
              onChange={(e) => setOperation(e.target.value)}
            >
              {catalog.operations.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.id} · v{o.version}
                  {o.preview_supported ? "" : " · preview unsupported"}
                </option>
              ))}
            </select>
          </label>
          <label>
            Patch name
            <input
              aria-label="Patch name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label>
            Patch semantic role
            <input
              aria-label="Patch semantic role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            />
          </label>
          <button
            disabled={
              !writable ||
              !catalog.operations.find((o) => o.id === operation)
                ?.topology_supported
            }
            onClick={() => void create(true)}
          >
            Add patch draft
          </button>
          <button disabled={!writable} onClick={() => void create(false)}>
            Add derived node draft
          </button>
          <h3>Boundary pick</h3>
          <p data-testid="picked-boundary">
            {picked || "Click a curve in 3D or choose an input in Properties."}
          </p>
          <p>
            Arrows indicate forward direction. Each slot has its own reverse
            control.
          </p>
          <details>
            <summary>Core capabilities</summary>
            <dl>
              {Object.entries(catalog.capabilities).map(([k, v]) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{String(v)}</dd>
                </div>
              ))}
            </dl>
          </details>
        </aside>
        <section>
          <div className="surface-controls">
            <label>
              <input
                type="checkbox"
                checked={wire}
                onChange={(e) => setWire(e.target.checked)}
              />
              Wireframe · preview topology
            </label>
            <label>
              Normals
              <select
                aria-label="Surface normals"
                value={normals}
                onChange={(e) => setNormals(e.target.value)}
              >
                <option value="off">Off</option>
                <option value="face">Face normals</option>
                <option value="vertex">Sample normals</option>
              </select>
            </label>
            <label>
              Patch colors
              <select
                aria-label="Patch colors"
                value={color}
                onChange={(e) => setColor(e.target.value)}
              >
                {["semantic", "operation", "validation", "continuity"].map(
                  (v) => (
                    <option key={v}>{v}</option>
                  ),
                )}
              </select>
            </label>
          </div>
          <div className={stale ? "surface-stale" : ""}>
            <SurfacePreview3D
              context={context}
              preview={preview}
              selected={selected}
              picked={picked.startsWith("cage:") ? picked.slice(5) : picked}
              wire={wire}
              normals={normals}
              color={color}
              onPatch={selectPatch}
              onBoundary={setPicked}
            />
          </div>
          {preview && (
            <p>
              {stale ? "STALE · " : ""}
              {preview.label} · {preview.quality} ·{" "}
              {preview.generation_ms.toFixed(1)} ms · revision{" "}
              {preview.revision.slice(0, 12)} · {preview.sampled_patches.length}{" "}
              resampled patches
            </p>
          )}
        </section>
        <aside>
          <h3>Properties {patch?.name || node?.id || ""}</h3>
          {node && metadata && (
            <>
              <code>{node.id}</code>
              <label>
                Node operation
                <select
                  aria-label="Node operation"
                  value={node.op}
                  disabled={!writable}
                  onChange={(e) =>
                    void commands([
                      {
                        type: "SetSurfaceOperation",
                        node_id: node.id,
                        op: e.target.value,
                      },
                    ])
                  }
                >
                  {catalog.operations.map((o) => (
                    <option key={o.id}>{o.id}</option>
                  ))}
                </select>
              </label>
              <p>
                {metadata.description} · {metadata.output_type}
              </p>
              {!metadata.preview_supported && <p>{metadata.limitation}</p>}
              {inputs.map((slot) => (
                <div className="surface-boundary" key={slot}>
                  <label>
                    {slot} →
                    <select
                      aria-label={"Boundary " + slot}
                      value={String(node.parameters[slot] || "")}
                      disabled={!writable}
                      onChange={(e) => void assign(slot, e.target.value)}
                    >
                      <option value="">Unassigned</option>
                      {graph?.nodes.map((n) => (
                        <option key={n.id} value={n.id}>
                          {n.id} · {n.op}
                        </option>
                      ))}
                      {context.cage_boundaries.map((c) => (
                        <option key={c.id} value={"cage:" + c.id}>
                          Cage · {c.id}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    aria-label={"Reverse " + slot}
                    aria-pressed={node.reversed?.includes(slot) || false}
                    disabled={!writable}
                    onClick={() =>
                      void commands([
                        {
                          type: "ReverseSurfaceBoundary",
                          node_id: node.id,
                          boundary: slot,
                        },
                      ])
                    }
                  >
                    {node.reversed?.includes(slot) ? "← REVERSE" : "→ FORWARD"}
                  </button>
                  <button
                    disabled={!writable || !picked}
                    onClick={() => void assign(slot, picked)}
                  >
                    Use picked {slot}
                  </button>
                </div>
              ))}
              {node.op === "coons" && (
                <p>
                  Coons corner correspondence: left(0) ↔ bottom(0), left(1) ↔
                  top(0), right(0) ↔ bottom(1), right(1) ↔ top(1).
                </p>
              )}
              {Object.entries(metadata.parameter_schema.properties)
                .filter(([key]) => !inputs.includes(key))
                .map(([key, schema]) => (
                  <Parameter
                    key={node.id + ":" + key + ":" + snapshot.revision}
                    name={key}
                    schema={schema}
                    value={node.parameters[key]}
                    disabled={!writable}
                    onSave={(value) =>
                      commands([
                        {
                          type: "SetSurfaceParameter",
                          node_id: node.id,
                          parameter: key,
                          value,
                        },
                      ])
                    }
                  />
                ))}
              <button
                disabled={!writable}
                onClick={() =>
                  void commands([
                    {
                      type: "SetSurfaceDraft",
                      node_id: node.id,
                      draft: !node.draft,
                    },
                  ])
                }
              >
                {node.draft ? "Mark node complete" : "Return node to draft"}
              </button>
              <button
                disabled={!writable}
                onClick={() =>
                  void commands([
                    { type: "DeleteSurfaceNode", node_id: node.id },
                  ])
                }
              >
                Delete derived node
              </button>
            </>
          )}
          {patch && (
            <>
              <Parameter
                key={patch.id + ":normal:" + snapshot.revision}
                name="expected_normal"
                schema={{ type: "array" }}
                value={patch.settings.normal || [0, 0, 1]}
                disabled={!writable}
                onSave={(normal) =>
                  commands([
                    { type: "SetSurfaceNormal", patch_id: patch.id, normal },
                  ])
                }
              />

              <label>
                Material role
                <select
                  aria-label="Surface material role"
                  value={patch.material_role || "generic"}
                  disabled={!writable}
                  onChange={(e) =>
                    void commands([
                      {
                        type: "SetSurfaceMaterialRole",
                        patch_id: patch.id,
                        material_role: e.target.value,
                      },
                    ])
                  }
                >
                  {[
                    "body_paint",
                    "glass",
                    "trim",
                    "tire",
                    "light",
                    "interior",
                    "generic",
                  ].map((r) => (
                    <option key={r}>{r}</option>
                  ))}
                </select>
              </label>
              <label>
                <input
                  type="checkbox"
                  aria-label="Mirror Y=0"
                  disabled={!writable}
                  checked={patch.settings.mirror || false}
                  onChange={(e) =>
                    void commands([
                      {
                        type: "SetSurfaceMirror",
                        patch_id: patch.id,
                        enabled: e.target.checked,
                      },
                    ])
                  }
                />
                Mirror Y=0 · {patch.id}.mirror
              </label>
              {["U", "V"].map((axis, i) => (
                <label key={axis}>
                  Resolution {axis}
                  <input
                    aria-label={"Resolution " + axis}
                    type="number"
                    min="1"
                    max="64"
                    defaultValue={patch.resolution[i]}
                    key={snapshot.revision + axis}
                    disabled={!writable}
                    onBlur={(e) => {
                      const value = Number(e.target.value);
                      if (value !== patch.resolution[i])
                        void commands([
                          {
                            type: "SetSurfaceResolution",
                            patch_id: patch.id,
                            resolution: patch.resolution.map((x, j) =>
                              j === i ? value : x,
                            ),
                          },
                        ]);
                    }}
                  />
                </label>
              ))}
              <Support
                key={patch.id + snapshot.revision}
                disabled={!writable}
                schedules={{ u: patch.us || [], v: patch.vs || [] }}
                onEdit={(type, axis, position) =>
                  commands([{ type, patch_id: patch.id, axis, position }])
                }
              />
              <button
                disabled={!writable}
                onClick={() =>
                  void commands([
                    { type: "DeleteSurfacePatch", patch_id: patch.id },
                  ])
                }
              >
                Delete selected patch
              </button>
            </>
          )}
        </aside>
      </div>
      <section className="surface-bottom">
        <div>
          <h3>Dependency DAG</h3>
          {graph?.nodes.map((n) => (
            <button
              key={n.id}
              aria-pressed={n.id === node?.id}
              onClick={() => {
                setNodeID(n.id);
                setSelected(
                  graph.patches.find((p) => p.sample === n.id)?.id || "",
                );
              }}
            >
              <code>{n.id}</code> ←{" "}
              {n.dependencies.join(", ") || "source parameters"} ·{" "}
              {n.draft ? "DRAFT" : "VALID"}
            </button>
          ))}
        </div>
        <div>
          <h3>Validation</h3>
          <button
            disabled={busy || !graph}
            onClick={() =>
              void validateDraft().catch((e) => setError(String(e)))
            }
          >
            Validate canonical graph
          </button>
          <ul>
            {(validation || context.validation).map((r, i) => (
              <li key={i}>
                <strong>
                  {r.category.toUpperCase()} · {r.status}
                </strong>{" "}
                {r.message}
              </li>
            ))}
          </ul>
          {preview &&
            Object.entries(preview.corners).map(([id, rows]) => (
              <details key={id} open={node?.id === id}>
                <summary>{id} · corner gaps</summary>
                {rows.map((r, i) => (
                  <p key={i}>
                    {r.connection}: {r.gap_m.toExponential(3)} m /{" "}
                    {r.tolerance_m} m · {r.status}
                  </p>
                ))}
              </details>
            ))}
        </div>
        <div>
          <h3>Adjacency / continuity</h3>
          {graph && (
            <AdjacencyEditor
              key={snapshot.revision}
              graph={graph}
              disabled={!writable}
              onSave={(adjacency) =>
                commands([{ type: "SetSurfaceAdjacency", adjacency }])
              }
            />
          )}
          <p>
            Canonical shared boundaries and declared connections; no
            proximity-only matching. G0 gaps and G1-like sampled normal
            compatibility.
          </p>
          {preview?.adjacency.map((a, i) => (
            <button
              key={i}
              onClick={() => {
                selectPatch(a.a);
                setPicked(a.b);
                setColor("continuity");
              }}
            >
              {a.a} {a.edge_a} ↔ {a.b} {a.edge_b}
              <br />
              {a.status} · max {a.max_gap_m?.toExponential(3)} m · RMS{" "}
              {a.rms_gap_m?.toExponential(3)} m · tolerance {a.tolerance_m} m
              <br />
              Normal angle {a.normal_angle_max_deg?.toFixed(3)}° · G1-like; no
              strict G1/G2 claim
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}
function Parameter({
  name,
  schema,
  value,
  disabled,
  onSave,
}: {
  name: string;
  schema: Schema;
  value: unknown;
  disabled: boolean;
  onSave: (v: unknown) => Promise<unknown>;
}) {
  const [draft, setDraft] = useState<unknown>(
      value ??
        (schema.type === "array" ? "" : schema.type === "number" ? 0 : ""),
    ),
    [error, setError] = useState("");
  const array = schema.type === "array";
  return (
    <div className="surface-parameter">
      {array ? (
        <label>
          {name}
          <textarea
            aria-label={"Parameter " + name}
            value={typeof draft === "string" ? draft : JSON.stringify(draft)}
            disabled={disabled}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Numeric array"
          />
        </label>
      ) : (
        <SchemaField
          label={"Parameter " + name}
          schema={schema}
          value={draft}
          onChange={setDraft}
          disabled={disabled}
        />
      )}
      <button
        disabled={disabled}
        onClick={() => {
          try {
            const v =
              array && typeof draft === "string" ? JSON.parse(draft) : draft;
            void onSave(v).then(() => setError(""));
          } catch {
            setError("Enter a valid numeric array.");
          }
        }}
      >
        Apply {name}
      </button>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
function Support({
  disabled,
  schedules,
  onEdit,
}: {
  disabled: boolean;
  schedules: { u: number[]; v: number[] };
  onEdit: (type: string, axis: string, position: number) => Promise<unknown>;
}) {
  const [position, setPosition] = useState(0.03),
    [axis, setAxis] = useState("u");
  return (
    <details>
      <summary>Support rows · sampling position</summary>
      <p>
        Explicit U/V schedules. Strength and offset have no independent core
        support-row semantics.
      </p>
      <select
        aria-label="Support axis"
        value={axis}
        onChange={(e) => setAxis(e.target.value)}
      >
        <option>u</option>
        <option>v</option>
      </select>
      <input
        aria-label="Support position"
        type="number"
        min="0.0001"
        max="0.9999"
        step=".01"
        value={position}
        onChange={(e) => setPosition(Number(e.target.value))}
      />
      <button
        disabled={disabled}
        onClick={() => void onEdit("AddSurfaceSupport", axis, position)}
      >
        Add support row
      </button>
      {schedules[axis as "u" | "v"]
        .filter((x) => x > 0 && x < 1)
        .map((x) => (
          <button
            disabled={disabled}
            key={x}
            onClick={() => void onEdit("RemoveSurfaceSupport", axis, x)}
          >
            Remove {axis}={x}
          </button>
        ))}
    </details>
  );
}

function AdjacencyEditor({
  graph,
  disabled,
  onSave,
}: {
  graph: SurfaceGraph;
  disabled: boolean;
  onSave: (a: Adjacency[]) => Promise<unknown>;
}) {
  const first = graph.adjacency?.[0];
  const [a, setA] = useState(first?.a || graph.patches[0]?.id || ""),
    [b, setB] = useState(first?.b || graph.patches[1]?.id || ""),
    [edgeA, setEdgeA] = useState(first?.edge_a || "right"),
    [edgeB, setEdgeB] = useState(first?.edge_b || "left"),
    [reverse, setReverse] = useState(first?.reverse || false),
    [tolerance, setTolerance] = useState(first?.tolerance_m || 0.0001);
  return (
    <details>
      <summary>Declare adjacency</summary>
      <label>
        Patch A
        <select
          aria-label="Adjacency patch A"
          value={a}
          onChange={(e) => setA(e.target.value)}
        >
          {graph.patches.map((p) => (
            <option key={p.id} value={p.id}>
              {p.id}
            </option>
          ))}
        </select>
      </label>
      <label>
        Patch B
        <select
          aria-label="Adjacency patch B"
          value={b}
          onChange={(e) => setB(e.target.value)}
        >
          {graph.patches.map((p) => (
            <option key={p.id} value={p.id}>
              {p.id}
            </option>
          ))}
        </select>
      </label>
      {[
        ["A", edgeA, setEdgeA],
        ["B", edgeB, setEdgeB],
      ].map(([label, value, set]) => (
        <label key={String(label)}>
          Edge {String(label)}
          <select
            aria-label={"Adjacency edge " + String(label)}
            value={String(value)}
            onChange={(e) => (set as (s: string) => void)(e.target.value)}
          >
            {["bottom", "top", "left", "right"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
      ))}
      <label>
        <input
          aria-label="Adjacency reversed"
          type="checkbox"
          checked={reverse}
          onChange={(e) => setReverse(e.target.checked)}
        />
        Reverse correspondence
      </label>
      <label>
        Gap tolerance (m)
        <input
          aria-label="Adjacency tolerance"
          type="number"
          step=".0001"
          value={tolerance}
          onChange={(e) => setTolerance(Number(e.target.value))}
        />
      </label>
      <button
        disabled={disabled || !a || !b || a === b}
        onClick={() =>
          void onSave([
            ...(graph.adjacency || []).filter((r) => r.a !== a || r.b !== b),
            {
              a,
              b,
              edge_a: edgeA,
              edge_b: edgeB,
              reverse,
              tolerance_m: tolerance,
            },
          ])
        }
      >
        Save adjacency
      </button>
    </details>
  );
}
