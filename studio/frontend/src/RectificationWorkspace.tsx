import { useEffect, useRef, useState } from "react";
import type { EditorClient } from "./api";
import type { Reference, Snapshot, View } from "./types";
import type {
  Anchor,
  Candidate,
  ReconciliationContext,
  ReconciliationRequest,
} from "./reconciliation-types";
import { RectificationGraphs, number } from "./RectificationGraphs";
import "./rectification.css";
const views: View[] = ["front", "side", "rear", "top"];
const clone = <T,>(v: T): T => structuredClone(v);
export function RectificationWorkspace({
  snapshot,
  client,
}: {
  snapshot: Snapshot;
  client: EditorClient;
}) {
  const [view, setView] = useState<View>("top"),
    [context, setContext] = useState<ReconciliationContext | null>(null),
    [draft, setDraft] = useState<ReconciliationRequest | null>(null),
    [selected, setSelected] = useState<Candidate | null>(null),
    [comparison, setComparison] = useState<Candidate[]>([]),
    [creator, setCreator] = useState(""),
    [reason, setReason] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [dirty, setDirty] = useState(false),
    [confirm, setConfirm] = useState(false),
    [datums, setDatums] = useState(false),
    [replace, setReplace] = useState(false);
  const seq = useRef(0),
    latest = useRef(snapshot);
  latest.current = snapshot;
  const base = `/projects/${snapshot.id}`,
    url = `/api/v1${base}`;
  async function refresh(keep = true, candidateId = selected?.id) {
    const token = ++seq.current;
    try {
      const c = await client.api.call<ReconciliationContext>(
        `${base}/reconciliation?view=${view}`,
      );
      if (token !== seq.current) return;
      setContext(c);
      setError(c.issue || "");
      if (!keep || !draft) {
        setDraft(c.default_request ? clone(c.default_request) : null);
        setDirty(false);
      }
      if (c.read_only) setSelected((c.candidates[0] as Candidate) || null);
      else if (keep && candidateId) {
        const p = await client.api.call<Candidate>(
          `${base}/reconciliation/${candidateId}`,
        );
        if (token === seq.current) setSelected(p);
      }
    } catch (e) {
      if (token === seq.current) setError((e as Error).message);
    }
  }
  useEffect(() => {
    setContext(null);
    setSelected(null);
    setComparison([]);
    setDraft(null);
    setDirty(false);
    void refresh(false);
    return () => {
      seq.current++;
    };
  }, [snapshot.id, view]);
  useEffect(() => {
    void refresh();
    setConfirm(false);
    setComparison([]);
  }, [snapshot.revision]);
  function edit(change: Partial<ReconciliationRequest>) {
    if (!draft) return;
    setDraft({ ...draft, ...change });
    setDirty(true);
    setConfirm(false);
  }
  function anchor(index: number, change: Partial<Anchor>) {
    if (!draft) return;
    edit({
      anchors: draft.anchors.map((a, i) =>
        i === index ? { ...a, ...change } : a,
      ),
    });
  }
  async function act(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function select(id: string) {
    await act(async () => {
      const p = await client.api.call<Candidate>(
        `${base}/reconciliation/${id}`,
      );
      setSelected(p);
      setDraft(clone(p.request));
      setDirty(false);
      setConfirm(false);
    });
  }
  async function generate() {
    if (!draft) return;
    await act(async () => {
      const start = snapshot.revision;
      const p = await client.api.post<Candidate>(`${base}/reconciliation`, {
        expected_revision: start,
        request: draft,
        creator,
        confirm_datums: datums,
      });
      if (latest.current.revision !== start)
        throw new Error("Evidence changed; reload candidate status.");
      setSelected(p);
      setDirty(false);
      setConfirm(false);
      await refresh(true, p.id);
    });
  }
  const p = selected,
    r = p?.report,
    readonly = !!context?.read_only || snapshot.read_only;
  const stale =
    !!p &&
    (p.freshness === "STALE" ||
      p.status === "STALE" ||
      (!p.active &&
        p.source_revision !== undefined &&
        p.source_revision !== snapshot.revision));
  const canActivate =
    !!p &&
    !!r?.eligible &&
    !stale &&
    !dirty &&
    !p.active &&
    p.status !== "REJECTED" &&
    client.writable &&
    confirm &&
    !busy;
  const cal = context?.calibration,
    refs = context?.references || snapshot.references;
  const source = refs.find(
    (r) =>
      r.role === (cal?.reference_id || draft?.reference_role || "multiview"),
  );
  const gaugeView = draft?.gauge_view || "side",
    gaugeCal = context?.views?.[gaugeView],
    gauge = refs.find(
      (r) => r.role === (gaugeCal?.reference_id || "multiview"),
    );
  const previous = cal?.source_history?.at(-1),
    old = previous && refs.find((r) => r.role === previous.reference_id);
  return (
    <main className="rect-workspace" data-testid="rectification-workspace">
      <header className="rect-toolbar">
        <div>
          <small>REFERENCE / RECTIFICATION</small>
          <h2>Reconcile the source</h2>
          <p>
            Candidate preview stays separate from active calibration. Original
            image bytes are preserved.
          </p>
        </div>
        <label>
          Source view
          <select
            aria-label="Rectification source view"
            value={view}
            onChange={(e) => setView(e.target.value as View)}
          >
            {views.map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <button disabled={busy} onClick={() => void refresh()}>
          Refresh evidence
        </button>
        <button
          disabled={!client.writable || !snapshot.history.undo || busy}
          onClick={() => void client.run("undo")}
        >
          Undo rectification / replacement
        </button>
      </header>
      {error && (
        <p role="alert" className="error-banner">
          {error}
        </p>
      )}
      {!context && <p role="status">Loading reference evidence…</p>}
      {cal?.source_state === "CALIBRATION_REQUIRED" && (
        <p className="rect-danger" role="status">
          CALIBRATION REQUIRED · New source framing is stale. Old observations
          remain bound to their original source. Review crop and calibration
          before generating candidates.
        </p>
      )}
      <div className="rect-reference-pair">
        <section>
          <h3>RAW SOURCE · {view.toUpperCase()}</h3>
          {source && (
            <AnchorImage
              url={`${url}/references/${source.id}/image`}
              reference={source}
              crop={cal?.crop || context?.views?.[view]?.crop}
              request={draft}
              onMove={(i, x) => anchor(i, { image: x })}
              readonly={readonly}
            />
          )}
        </section>
        <section>
          <h3>REFERENCE / GAUGE</h3>
          <label>
            Gauge view
            <select
              aria-label="Gauge view"
              value={gaugeView}
              disabled={readonly}
              onChange={(e) => edit({ gauge_view: e.target.value as View })}
            >
              {views.map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          {gauge && (
            <AnchorImage
              url={`${url}/references/${gauge.id}/image`}
              reference={gauge}
              crop={gaugeCal?.crop}
              readonly
            />
          )}
          <p>
            World correspondences provide independent evidence. Choosing a gauge
            does not refit world geometry.
          </p>
        </section>
      </div>
      {!readonly && draft && (
        <section className="rect-panel">
          <h3>
            Manual anchors ·{" "}
            {dirty
              ? "DRAFT — regenerate to evaluate"
              : "inspected candidate inputs"}
          </h3>
          <p>
            FIT builds the mapping. HELD_OUT must bind an independent measured
            correspondence. Every other critical correspondence remains held
            out. Locked datum coordinates cannot be dragged.
          </p>
          <div className="rect-controls">
            <label>
              Creator
              <input
                aria-label="Candidate creator"
                value={creator}
                onChange={(e) => setCreator(e.target.value)}
              />
            </label>
            <label>
              Axis
              <select
                aria-label="Rectification axis"
                value={draft.axis}
                onChange={(e) => edit({ axis: e.target.value as "u" | "v" })}
              >
                <option>u</option>
                <option>v</option>
              </select>
            </label>
            <label>
              Allowed scale change
              <input
                aria-label="Allowed scale change"
                type="number"
                min="0"
                max="0.1"
                step="0.01"
                value={draft.max_scale_change}
                onChange={(e) =>
                  edit({ max_scale_change: e.target.valueAsNumber })
                }
              />
            </label>
            <label>
              <input
                type="checkbox"
                checked={draft.allow_extrapolation}
                onChange={(e) =>
                  edit({ allow_extrapolation: e.target.checked })
                }
              />
              Allow explicit extrapolation
            </label>
          </div>
          <details>
            <summary>Authoritative datum / domain change</summary>
            <p>
              Separate confirmation is required for new image or affine domain
              endpoints. Datums stay exactly normalized 0/0 and 1/1.
            </p>
            <label>
              <input
                aria-label="Confirm datum domain change"
                type="checkbox"
                checked={datums}
                onChange={(e) => setDatums(e.target.checked)}
              />
              Confirm authoritative datum domain change
            </label>
            {(["image_domain_px", "affine_domain_px"] as const).map((key) => (
              <label key={key}>
                {key}
                {draft[key].map((v, i) => (
                  <input
                    key={i}
                    aria-label={`${key} ${i}`}
                    type="number"
                    disabled={!datums}
                    value={v}
                    onChange={(e) => {
                      const d = [...draft[key]];
                      d[i] = e.target.valueAsNumber;
                      edit({ [key]: d });
                    }}
                  />
                ))}
              </label>
            ))}
          </details>
          <div className="rect-table">
            <table aria-label="Anchor table">
              <thead>
                <tr>
                  {[
                    "Semantic ID",
                    "Source px",
                    "Source normalized",
                    "Affine normalized",
                    "Role",
                    "Confidence",
                    "Provenance",
                    "Measured observation",
                    "Datum",
                    "Remove",
                  ].map((v) => (
                    <th key={v}>{v}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {draft.anchors.map((a, i) => (
                  <tr key={a.id}>
                    <td>
                      <input
                        aria-label={`Semantic ${i}`}
                        value={a.semantic}
                        onChange={(e) =>
                          anchor(i, { semantic: e.target.value })
                        }
                      />
                    </td>
                    <td>
                      {number(
                        draft.image_domain_px[0] +
                          a.image *
                            (draft.image_domain_px[1] -
                              draft.image_domain_px[0]),
                      )}
                    </td>
                    <td>
                      <input
                        aria-label={`Source normalized ${i}`}
                        type="number"
                        step="0.001"
                        disabled={a.locked}
                        value={a.image}
                        onChange={(e) =>
                          anchor(i, { image: e.target.valueAsNumber })
                        }
                      />
                    </td>
                    <td>
                      <input
                        aria-label={`Affine normalized ${i}`}
                        type="number"
                        step="0.001"
                        disabled={a.locked}
                        value={a.world_normalized}
                        onChange={(e) =>
                          anchor(i, {
                            world_normalized: e.target.valueAsNumber,
                          })
                        }
                      />
                    </td>
                    <td>
                      <select
                        aria-label={`Anchor role ${i}`}
                        disabled={a.locked}
                        value={a.role}
                        onChange={(e) =>
                          anchor(i, { role: e.target.value as Anchor["role"] })
                        }
                      >
                        <option>FIT</option>
                        <option>HELD_OUT</option>
                      </select>
                    </td>
                    <td>
                      <input
                        aria-label={`Confidence ${i}`}
                        type="number"
                        min="0"
                        max="1"
                        step="0.1"
                        value={a.confidence}
                        onChange={(e) =>
                          anchor(i, { confidence: e.target.valueAsNumber })
                        }
                      />
                    </td>
                    <td>
                      <input
                        aria-label={`Provenance ${i}`}
                        value={a.provenance}
                        onChange={(e) =>
                          anchor(i, { provenance: e.target.value })
                        }
                      />
                    </td>
                    <td>
                      <input
                        aria-label={`Measured observation ${i}`}
                        value={a.observation_id || ""}
                        onChange={(e) => {
                          const anchors = clone(draft.anchors);
                          if (e.target.value)
                            anchors[i].observation_id = e.target.value;
                          else delete anchors[i].observation_id;
                          edit({ anchors });
                        }}
                      />
                    </td>
                    <td>{a.locked ? "LOCKED EXACT" : "unlocked"}</td>
                    <td>
                      <button
                        aria-label={`Remove anchor ${i}`}
                        disabled={a.locked}
                        onClick={() =>
                          edit({
                            anchors: draft.anchors.filter((_, j) => j !== i),
                          })
                        }
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            disabled={draft.anchors.length >= 64}
            onClick={() =>
              edit({
                anchors: [
                  ...draft.anchors,
                  {
                    id: "manual_" + crypto.randomUUID().replaceAll("-", ""),
                    semantic: "manual feature",
                    image: 0.5,
                    world_normalized: 0.5,
                    role: "FIT",
                    locked: false,
                    confidence: 1,
                    provenance: "Manual source anchor",
                  },
                ],
              })
            }
          >
            Add anchor
          </button>
          <button
            className="primary"
            disabled={
              busy ||
              !creator.trim() ||
              !client.writable ||
              cal?.source_state === "CALIBRATION_REQUIRED"
            }
            onClick={() => void generate()}
          >
            Generate Candidate
          </button>
        </section>
      )}
      <section className="rect-panel">
        <h3>Candidate archive · inactive until explicit activation</h3>
        <div className="rect-candidates">
          {context?.candidates
            .filter((c) => c.view === view || readonly)
            .map((c) => (
              <article key={c.id}>
                <strong>{c.creator}</strong>
                <code>{c.id.slice(0, 12)}</code>
                <span>
                  {c.status} · {c.active ? "ACTIVE" : "NOT ACTIVE"}
                </span>
                <button
                  disabled={readonly || busy}
                  onClick={() => void select(c.id)}
                >
                  Inspect {c.id.slice(0, 8)}
                </button>
                <label>
                  <input
                    aria-label={`Compare ${c.id}`}
                    type="checkbox"
                    checked={comparison.some((p) => p.id === c.id)}
                    disabled={
                      comparison.length >= 3 &&
                      !comparison.some((p) => p.id === c.id)
                    }
                    onChange={(e) => {
                      if (!e.target.checked)
                        setComparison(comparison.filter((p) => p.id !== c.id));
                      else
                        void act(async () => {
                          const p = readonly
                            ? (c as Candidate)
                            : await client.api.call<Candidate>(
                                `${base}/reconciliation/${c.id}`,
                              );
                          setComparison((old) =>
                            [...old.filter((x) => x.id !== p.id), p].slice(
                              0,
                              3,
                            ),
                          );
                        });
                    }}
                  />
                  Compare
                </label>
              </article>
            ))}
        </div>
      </section>
      {comparison.length > 0 && (
        <section className="rect-comparison" aria-label="Candidate comparison">
          {comparison.map((c) => (
            <div key={c.id}>
              <h3>{c.id.slice(0, 12)}</h3>
              <EvidenceSummary candidate={c} />
              <p>
                {c.request.anchors?.length || c.report.anchors.length} anchors
              </p>
              <details>
                <summary>Anchors and held-out residuals</summary>
                <pre>
                  {JSON.stringify(
                    { anchors: c.report.anchors, held_out: c.report.held_out },
                    null,
                    2,
                  )}
                </pre>
              </details>
            </div>
          ))}
        </section>
      )}
      {p && r && (
        <>
          <section
            className={"rect-panel " + (!r.eligible ? "rect-danger" : "")}
            aria-label="Candidate decision"
          >
            <h3>
              {stale ? "STALE" : p.status} ·{" "}
              {p.active ? "ACTIVE" : "NOT ACTIVE"} · {r.distortion}
            </h3>
            {dirty && (
              <p>
                DRAFT INPUTS CHANGED · displayed report belongs to the inspected
                candidate. Generate a new candidate to evaluate edits.
              </p>
            )}
            <EvidenceSummary candidate={p} />
            <ul>
              {r.reasons.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
            <p>
              Strictly monotonic: {r.strictly_monotonic ? "YES" : "NO"} ·
              Derivative positive: {r.derivative_positive ? "YES" : "NO"} ·
              Foldover: {r.foldover ? "YES" : "NO"}
            </p>
            {!readonly && (
              <>
                <label>
                  <input
                    aria-label="Confirm rectification activation"
                    type="checkbox"
                    checked={confirm}
                    onChange={(e) => setConfirm(e.target.checked)}
                  />
                  I inspected independent held-out evidence and confirm
                  activation into canonical calibration. Source review remains
                  required.
                </label>
                <button
                  className="primary"
                  disabled={!canActivate}
                  onClick={() =>
                    void act(async () => {
                      if (
                        await client.run("activate-rectification", {
                          candidate_id: p.id,
                          candidate_revision: p.revision,
                          confirm_activation: true,
                        })
                      )
                        await refresh();
                    })
                  }
                >
                  ACTIVATE RECTIFICATION
                </button>
                <label>
                  Rejection reason
                  <input
                    aria-label="Rejection reason"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                  />
                </label>
                <button
                  disabled={
                    busy ||
                    p.active ||
                    p.status === "REJECTED" ||
                    !reason.trim()
                  }
                  onClick={() =>
                    void act(async () => {
                      const q = await client.api.post<Candidate>(
                        `${base}/reconciliation/${p.id}/reject`,
                        { candidate_revision: p.revision, reason },
                      );
                      setSelected(q);
                      await refresh();
                    })
                  }
                >
                  REJECT CANDIDATE
                </button>
              </>
            )}
            {readonly && <button disabled>ACTIVATE RECTIFICATION</button>}
            <details>
              <summary>Provenance and algorithm</summary>
              <pre>
                {JSON.stringify(
                  {
                    creator: p.creator,
                    source_revision: p.source_revision,
                    source_hashes: p.source_hashes,
                    calibration_base: p.base_calibration_hash,
                    algorithm: p.algorithm,
                    parameters: p.request,
                    physical_basis: p.physical_basis,
                  },
                  null,
                  2,
                )}
              </pre>
            </details>
          </section>
          <RectificationGraphs candidate={p} />
          <Preview
            candidate={p}
            url={url}
            crop={cal?.crop || context?.views?.[view]?.crop}
          />
          <Residuals candidate={p} />
        </>
      )}
      {!readonly && (
        <section className="rect-panel">
          <h3>REPLACE / REGENERATE SOURCE VIEW</h3>
          <p>
            Import an immutable replacement for {view.toUpperCase()}. The
            original source is retained; framing, observations, candidates and
            reviews become stale. World geometry stays fixed.
          </p>
          <label>
            <input
              type="checkbox"
              aria-label="Confirm source replacement"
              checked={replace}
              onChange={(e) => setReplace(e.target.checked)}
            />
            Confirm replacement of this source view
          </label>
          <input
            type="file"
            aria-label="Replacement source image"
            accept="image/png,image/jpeg"
            disabled={!replace || !client.writable || busy}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f)
                void act(async () => {
                  await client.import(f, view);
                  setReplace(false);
                  await refresh();
                });
              e.target.value = "";
            }}
          />
          {old && source && previous && (
            <SourceComparison
              old={old}
              source={source}
              previousCrop={previous.crop}
              url={url}
              observations={snapshot.observations
                .filter(
                  (o) =>
                    o.view === view &&
                    o.reference_id === old.role &&
                    "pixel" in o,
                )
                .map((o) => ({
                  id: o.id,
                  pixel: ("pixel" in o ? o.pixel : []) as number[],
                }))}
            />
          )}
        </section>
      )}
    </main>
  );
}
function AnchorImage({
  url,
  reference,
  crop,
  request,
  onMove,
  readonly,
}: {
  url: string;
  reference: Reference;
  crop?: number[];
  request?: ReconciliationRequest | null;
  onMove?: (i: number, x: number) => void;
  readonly?: boolean;
}) {
  const [drag, setDrag] = useState<number | null>(null);
  const c = crop || [0, 0, ...reference.size],
    axis = request?.axis === "v" ? 1 : 0;
  return (
    <svg
      className="rect-source"
      viewBox={`${c[0]} ${c[1]} ${c[2] - c[0]} ${c[3] - c[1]}`}
      aria-label="Source anchors"
      onPointerMove={(e) => {
        if (drag === null || !request || !onMove) return;
        const svg = e.currentTarget,
          pt = svg.createSVGPoint();
        pt.x = e.clientX;
        pt.y = e.clientY;
        const p = pt.matrixTransform(svg.getScreenCTM()!.inverse());
        const value = axis ? p.y : p.x;
        onMove(
          drag,
          (value - request.image_domain_px[0]) /
            (request.image_domain_px[1] - request.image_domain_px[0]),
        );
      }}
      onPointerUp={() => setDrag(null)}
      onPointerCancel={() => setDrag(null)}
    >
      <image href={url} width={reference.size[0]} height={reference.size[1]} />
      {request?.anchors.map((a, i) => {
        const x =
            request.image_domain_px[0] +
            a.image * (request.image_domain_px[1] - request.image_domain_px[0]),
          size = (c[2] - c[0]) * 0.012;
        return (
          <g key={a.id} className={a.locked ? "locked" : "anchor"}>
            <line
              x1={axis ? c[0] : x}
              y1={axis ? x : c[1]}
              x2={axis ? c[2] : x}
              y2={axis ? x : c[3]}
              stroke={a.role === "FIT" ? "#087f76" : "#a55400"}
              strokeWidth={size / 6}
              strokeDasharray={
                a.role === "HELD_OUT" ? `${size} ${size}` : undefined
              }
            />
            <circle
              data-testid={`anchor-handle-${i}`}
              aria-label={`${a.semantic} ${a.locked ? "locked" : "drag anchor"}`}
              cx={axis ? (c[0] + c[2]) / 2 : x}
              cy={axis ? x : (c[1] + c[3]) / 2}
              r={size}
              fill={a.locked ? "#fff" : "#46d4c4"}
              stroke="#142d38"
              strokeWidth={size / 3}
              onPointerDown={(e) => {
                if (readonly || a.locked) return;
                e.currentTarget.ownerSVGElement?.setPointerCapture(e.pointerId);
                setDrag(i);
              }}
            >
              <title>
                {a.semantic} · {a.role} ·{" "}
                {a.locked ? "LOCKED" : number(a.image, 9)}
              </title>
            </circle>
          </g>
        );
      })}
    </svg>
  );
}
function EvidenceSummary({ candidate: c }: { candidate: Candidate }) {
  const r = c.report;
  return (
    <div className="rect-summary">
      <p>
        Eligibility: {r.eligible ? "ELIGIBLE_FOR_ACTIVATION" : "INELIGIBLE"} ·{" "}
        {c.freshness}
      </p>
      <p>
        Between datums: {number(r.between_datums?.maximum_correction_px)} px ·{" "}
        {number(r.between_datums?.maximum_equivalent_mm)} mm equivalent source
        correction.
      </p>
      <p>
        Whole crop: {number(r.whole_crop?.maximum_correction_px)} px ·{" "}
        {number(r.whole_crop?.maximum_absolute_normalized, 6)} normalized ·{" "}
        {number(r.whole_crop?.maximum_equivalent_mm)} mm equivalent source
        correction.
      </p>
      <p>
        Local scale:{" "}
        {r.local_scale_range?.map((x) => number(x, 9)).join(" – ") ||
          "unavailable"}
        ; allowed {r.allowed_scale?.join(" – ")}.
      </p>
      <p>
        RMS correction, fit / held-out / all: {number(r.rms_fit_correction_px)}{" "}
        / {number(r.rms_heldout_correction_px)} /{" "}
        {number(r.rms_all_landmark_correction_px)} px.
      </p>
      <p>
        Extrapolated fraction: {number((r.extrapolation?.fraction || 0) * 100)}%
        · front overhang{" "}
        {r.extrapolation?.front_range?.map((x) => number(x)).join("…") ||
          "none"}{" "}
        · rear overhang{" "}
        {r.extrapolation?.rear_range?.map((x) => number(x)).join("…") || "none"}
      </p>
      <p>{r.extrapolation?.policy}</p>
      {r.overhangs && (
        <p>
          Front overhang correction:{" "}
          {number(r.overhangs.front?.maximum_correction_px)} px; rear overhang
          correction: {number(r.overhangs.rear?.maximum_correction_px)} px. Each
          overhang is audited separately.
        </p>
      )}
    </div>
  );
}
function Residuals({ candidate }: { candidate: Candidate }) {
  const r = candidate.report;
  return (
    <section className="rect-panel">
      <h3>Independent held-out evidence</h3>
      {r.before && r.after && (
        <table aria-label="Before after consistency">
          <thead>
            <tr>
              <th>Metric</th>
              <th>BEFORE</th>
              <th>AFTER</th>
            </tr>
          </thead>
          <tbody>
            {(
              [
                "max_critical_px",
                "mean_critical_px",
                "held_out_rms_px",
                "failed_critical",
              ] as const
            ).map((k) => (
              <tr key={k}>
                <th>{k}</th>
                <td>{number(r.before![k])}</td>
                <td>{number(r.after![k])}</td>
              </tr>
            ))}
            <tr>
              <th>local scale</th>
              <td>1 affine</td>
              <td>{r.local_scale_range?.join(" – ")}</td>
            </tr>
            <tr>
              <th>max correction px</th>
              <td>0</td>
              <td>{number(r.whole_crop?.maximum_correction_px)}</td>
            </tr>
          </tbody>
        </table>
      )}
      <div className="rect-table">
        <table aria-label="Held-out residual report">
          <thead>
            <tr>
              {[
                "Landmark",
                "Raw px",
                "Rectified px",
                "Delta px",
                "Tolerance px",
                "Result",
                "Region",
              ].map((s) => (
                <th key={s}>{s}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {r.held_out.map((e, i) => (
              <tr key={e.id || i}>
                <td>{e.semantic || e.id || "Historical correction"}</td>
                <td>{number(e.raw_residual_px)}</td>
                <td>{number(e.rectified_residual_px)}</td>
                <td>{number(e.delta_px)}</td>
                <td>{number(e.tolerance_px)}</td>
                <td>
                  {e.status ||
                    "Historical correction only; no independent held-out claim"}
                </td>
                <td>
                  {"extrapolated" in e && e.extrapolated
                    ? "EXTRAPOLATED"
                    : "between datums"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!r.before && (
        <p>
          Historical Mark II evidence records correction magnitude, not an
          independent held-out residual pass.
        </p>
      )}
    </section>
  );
}
function Preview({
  candidate: p,
  url,
  crop,
}: {
  candidate: Candidate;
  url: string;
  crop?: number[];
}) {
  const [mode, setMode] = useState("side-by-side"),
    [opacity, setOpacity] = useState(0.5),
    [flick, setFlick] = useState(false),
    [grid, setGrid] = useState(true),
    [features, setFeatures] = useState(true);
  useEffect(() => {
    if (mode !== "flicker") return;
    const t = setInterval(() => setFlick((v) => !v), 600);
    return () => clearInterval(t);
  }, [mode]);
  const c = crop || [0, 0, 256, 256],
    w = c[2] - c[0],
    h = c[3] - c[1],
    r = p.report;
  const src = (kind: string) => `${url}/reconciliation/${p.id}/preview/${kind}`;
  function image(kind: "raw" | "rectified" | "difference", alpha = 1) {
    return (
      <svg
        className="rect-preview"
        viewBox={`0 0 ${w} ${h}`}
        aria-label={`${kind} preview`}
        style={{ opacity: alpha }}
      >
        <image
          href={src(kind)}
          width={w}
          height={h}
          preserveAspectRatio="none"
        />
        {grid && (
          <g stroke="#176ac0" strokeWidth={w / 800} opacity=".7">
            {Array.from({ length: 11 }, (_, i) => {
              const x = c[0] + (w * i) / 10,
                sample = r.samples?.reduce((a, b) =>
                  Math.abs(a.source_px - x) < Math.abs(b.source_px - x) ? a : b,
                ),
                q =
                  kind === "rectified" && p.request.axis === "u" && sample
                    ? sample.target_px - c[0]
                    : (w * i) / 10;
              const y = c[1] + (h * i) / 10,
                sy = r.samples?.reduce((a, b) =>
                  Math.abs(a.source_px - y) < Math.abs(b.source_px - y) ? a : b,
                ),
                v =
                  kind === "rectified" && p.request.axis === "v" && sy
                    ? sy.target_px - c[1]
                    : (h * i) / 10;
              return (
                <g key={i}>
                  <line x1={q} x2={q} y1="0" y2={h} />
                  <line x1="0" x2={w} y1={v} y2={v} />
                </g>
              );
            })}
          </g>
        )}
        {features &&
          r.feature_comparison?.map((e) => {
            const a =
                kind === "rectified" ? e.rectified_pixel || e.pixel : e.pixel,
              b =
                kind === "rectified"
                  ? e.projected_affine
                  : e.projected_raw || e.projected_affine;
            return (
              <g key={e.id} stroke="#9c2c13" strokeWidth={w / 250}>
                <line
                  x1={a[0] - c[0]}
                  y1={a[1] - c[1]}
                  x2={b[0] - c[0]}
                  y2={b[1] - c[1]}
                />
                <circle
                  cx={a[0] - c[0]}
                  cy={a[1] - c[1]}
                  r={w / 120}
                  fill="#12c9ba"
                />
                <path
                  d={`M${b[0] - c[0] - w / 100} ${b[1] - c[1]} h${w / 50} m${-w / 100} ${-w / 100} v${w / 50}`}
                />
                <title>{e.semantic} · observed ● / projected +</title>
              </g>
            );
          })}
      </svg>
    );
  }
  return (
    <section className="rect-panel">
      <h3>RAW SOURCE / RECTIFIED PREVIEW</h3>
      <div className="rect-controls">
        <label>
          Preview mode
          <select
            aria-label="Preview mode"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            {["side-by-side", "opacity", "flicker", "difference"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Preview opacity
          <input
            aria-label="Preview opacity"
            type="range"
            min="0"
            max="1"
            step=".01"
            value={opacity}
            onChange={(e) => setOpacity(e.target.valueAsNumber)}
          />
        </label>
        <label>
          <input
            type="checkbox"
            checked={grid}
            onChange={(e) => setGrid(e.target.checked)}
          />
          Diagnostic source grid
        </label>
        <label>
          <input
            type="checkbox"
            checked={features}
            onChange={(e) => setFeatures(e.target.checked)}
          />
          Observed ● / projected + features
        </label>
      </div>
      <div
        className={
          mode === "side-by-side" ? "rect-reference-pair" : "rect-overlay"
        }
      >
        {mode === "side-by-side" ? (
          <>
            <div>
              <p>RAW SOURCE</p>
              {image("raw")}
            </div>
            <div>
              <p>RECTIFIED PREVIEW</p>
              {image("rectified")}
            </div>
          </>
        ) : mode === "difference" ? (
          image("difference")
        ) : mode === "flicker" ? (
          image(flick ? "raw" : "rectified")
        ) : (
          <>
            {image("raw")}
            {image("rectified", opacity)}
          </>
        )}
      </div>
      <p>
        Equivalent source correction describes the image mapping, not a physical
        change to the vehicle. Grid positions and previews use core samples and
        inverse mapping.
      </p>
    </section>
  );
}
function SourceComparison({
  old,
  source,
  previousCrop,
  url,
  observations,
}: {
  old: Reference;
  source: Reference;
  previousCrop: number[];
  url: string;
  observations: { id: string; pixel: number[] }[];
}) {
  const [overlay, setOverlay] = useState(false),
    [transfer, setTransfer] = useState(true),
    [opacity, setOpacity] = useState(0.5);
  return (
    <section aria-label="Source replacement comparison">
      <h3>Retained old source / replacement</h3>
      <label>
        <input
          type="checkbox"
          checked={overlay}
          onChange={(e) => setOverlay(e.target.checked)}
        />
        Overlay sources
      </label>
      <label>
        Replacement opacity
        <input
          type="range"
          aria-label="Replacement opacity"
          min="0"
          max="1"
          step=".01"
          value={opacity}
          onChange={(e) => setOpacity(e.target.valueAsNumber)}
        />
      </label>
      <label>
        <input
          type="checkbox"
          checked={transfer}
          onChange={(e) => setTransfer(e.target.checked)}
        />
        Landmark transfer preview · PROPOSAL ONLY
      </label>
      <div className={overlay ? "rect-overlay" : "rect-reference-pair"}>
        {[old, source].map((ref, i) => (
          <svg
            key={ref.id}
            style={{ opacity: overlay && i ? opacity : 1 }}
            viewBox={`0 0 ${ref.size[0]} ${ref.size[1]}`}
            aria-label={i ? "Replacement source" : "Retained old source"}
          >
            <image
              href={`${url}/references/${ref.id}/image`}
              width={ref.size[0]}
              height={ref.size[1]}
            />
            {transfer &&
              observations.map((o) => (
                <circle
                  key={o.id}
                  cx={(o.pixel[0] / old.size[0]) * ref.size[0]}
                  cy={(o.pixel[1] / old.size[1]) * ref.size[1]}
                  r={ref.size[0] / 100}
                  fill="none"
                  stroke="#d15220"
                  strokeWidth={ref.size[0] / 350}
                >
                  <title>
                    {o.id} ·{" "}
                    {i
                      ? "unmeasured transfer proposal"
                      : "original measured point"}
                  </title>
                </circle>
              ))}
          </svg>
        ))}
      </div>
      <p>
        Proposal uses normalized full-image coordinates only; no observations
        are transferred or measured. Prior crop: {previousCrop.join(", ")}.
        Recalibrate the replacement before creating new measured observations.
      </p>
    </section>
  );
}
