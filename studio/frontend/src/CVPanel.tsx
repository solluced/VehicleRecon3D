import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./cv.css";
import type { EditorClient } from "./api";
import type { Reference, Snapshot, View } from "./types";
import type {
  AssistCanvas,
  AssistTool,
  CVJob,
  CVProposal,
  CVProvider,
} from "./cv-types";

type Props = {
  snapshot: Snapshot;
  client: EditorClient;
  reference: Reference;
  view: View;
  initialTool: AssistTool;
  activation: number;
  onCanvas: (value: AssistCanvas | undefined) => void;
  onExit: () => void;
};
type Context = { crop: number[]; crop_id: string; source_sha256: string };
type Stroke = {
  label: "foreground" | "background";
  points: number[][];
  radius: number;
};
const capability = (tool: AssistTool) =>
  tool === "foreground" || tool === "background"
    ? "segment_object"
    : tool === "magic_select"
      ? "segment_object"
      : tool;
const roundBox = (a: number[], b: number[], crop: number[]) => [
  Math.max(crop[0], Math.floor(Math.min(a[0], b[0]))),
  Math.max(crop[1], Math.floor(Math.min(a[1], b[1]))),
  Math.min(crop[2], Math.ceil(Math.max(a[0], b[0]))),
  Math.min(crop[3], Math.ceil(Math.max(a[1], b[1]))),
];

export function CVPanel(props: Props) {
  const { client, snapshot, reference, view, onCanvas } = props;
  const [providers, setProviders] = useState<CVProvider[]>([]),
    [provider, setProvider] = useState("");
  const [context, setContext] = useState<Context | null>(null),
    [tool, setTool] = useState<AssistTool>(props.initialTool);
  const [proposal, setProposal] = useState<CVProposal | null>(null),
    [edge, setEdge] = useState<CVProposal | null>(null);
  const [selected, setSelected] = useState<string[]>([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [job, setJob] = useState<CVJob | null>(null);
  const [preset, setPreset] = useState("Normal"),
    [threshold, setThreshold] = useState(140),
    [radius, setRadius] = useState(24);
  const [attraction, setAttraction] = useState(5),
    [smoothness, setSmoothness] = useState(0.3),
    [contrast, setContrast] = useState(0);
  const [roi, setRoi] = useState<number[]>([0, 0, ...reference.size]),
    [box, setBox] = useState<number[] | undefined>();
  const [preview, setPreview] = useState<number[][]>([]),
    [trace, setTrace] = useState<CVProposal | null>(null),
    [anchor, setAnchor] = useState<number[] | null>(null);
  const [strokes, setStrokes] = useState<Stroke[]>([]),
    [brushRadius, setBrushRadius] = useState(8);
  const [visible, setVisible] = useState(true),
    [original, setOriginal] = useState(false),
    [opacity, setOpacity] = useState(0.9);
  const [edgeVisible, setEdgeVisible] = useState(false),
    [edgeOpacity, setEdgeOpacity] = useState(0.65),
    [maskVisible, setMaskVisible] = useState(true);
  const [role, setRole] = useState("UNKNOWN"),
    [verified, setVerified] = useState(false);
  const [tolerance, setTolerance] = useState(2),
    [maximum, setMaximum] = useState(256),
    [corners, setCorners] = useState(true),
    [spline, setSpline] = useState(false);
  const [trimStart, setTrimStart] = useState(0),
    [trimEnd, setTrimEnd] = useState(1),
    [editIndex, setEditIndex] = useState(0),
    [editXY, setEditXY] = useState(["0", "0"]);
  const [previewTimes, setPreviewTimes] = useState<number[]>([]),
    [commitTimes, setCommitTimes] = useState<number[]>([]);
  const mounted = useRef(true),
    jobs = useRef(new Set<string>()),
    generation = useRef(0),
    previewRunning = useRef(false),
    previewTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const trail = useRef<number[][]>([]),
    drag = useRef<number[][]>([]),
    lastPreviewRequest = useRef(0),
    pointerAt = useRef(0),
    latest = useRef<any>(null);
  const base = `/projects/${snapshot.id}`,
    sourceToken = `${snapshot.id}:${reference.id}:${view}:${snapshot.revision}`;
  const token = useRef(sourceToken);
  token.current = sourceToken;
  const available =
    providers.find((p) => p.provider_id === provider)?.available === true;
  const component = proposal?.components.find((c) => c.id === selected[0]);
  const active = proposal?.status === "ACTIVE" && !client.state.conflict;

  const cancelAll = useCallback(() => {
    generation.current++;
    if (previewTimer.current) clearTimeout(previewTimer.current);
    for (const id of jobs.current)
      void client.api
        .post(base + "/cv-jobs/" + id + "/cancel", {})
        .catch(() => {});
    jobs.current.clear();
    previewRunning.current = false;
  }, [base, client]);
  useEffect(() => {
    mounted.current = true;
    let alive = true;
    void client.api
      .call<{ providers: CVProvider[] }>("/cv/providers")
      .then((v) => {
        if (alive) {
          setProviders(v.providers);
          setProvider(v.providers[0]?.provider_id || "");
        }
      })
      .catch((e) => alive && setError(e.message));
    return () => {
      alive = false;
      mounted.current = false;
      cancelAll();
      onCanvas(undefined);
    };
  }, [base, reference.id, view]);
  useEffect(() => {
    let alive = true;
    cancelAll();
    setEdge(null);
    setTrace(null);
    setAnchor(null);
    setPreview([]);
    trail.current = [];
    void client.api
      .call<Context>(
        `${base}/cv-context?reference_id=${reference.id}&view=${view}&expected_revision=${snapshot.revision}`,
      )
      .then((v) => {
        if (alive) {
          setContext(v);
          setRoi((old) =>
            context && context.crop.join(",") === v.crop.join(",")
              ? old
              : v.crop,
          );
        }
      })
      .catch((e) => alive && setError(e.message));
    setProposal((p) =>
      p?.status === "ACTIVE"
        ? {
            ...p,
            status: "STALE",
            components: p.components.map((c) => ({
              ...c,
              status: c.status === "ACTIVE" ? "STALE" : c.status,
            })),
          }
        : p,
    );
    return () => {
      alive = false;
    };
  }, [sourceToken]);
  useEffect(() => {
    if (client.state.conflict) {
      cancelAll();
      setProposal((p) =>
        p?.status === "ACTIVE" ? { ...p, status: "STALE" } : p,
      );
    }
  }, [client.state.conflict]);
  useEffect(() => {
    setTool(props.initialTool);
    setAnchor(null);
    setTrace(null);
    setPreview([]);
    trail.current = [];
  }, [props.initialTool, props.activation]);
  useEffect(() => {
    if (component) {
      setRole(component.semantic_role);
      setTrimEnd(
        (component.working_points || component.original_points || []).length -
          1,
      );
    }
  }, [component?.id, proposal?.proposal_id]);

  const choose = (p: CVProposal) => {
    setProposal(p);
    setSelected(
      p.components
        .filter((c) => c.status === "ACTIVE")
        .slice(0, 1)
        .map((c) => c.id),
    );
    setError("");
  };
  async function run(
    cap: string,
    parameters: Record<string, unknown>,
    parent?: string,
    supersedes?: string,
  ) {
    if (!available)
      throw new Error(
        "Provider unavailable. Choose an installed provider explicitly or use manual tools.",
      );
    const pinned = token.current,
      epoch = generation.current;
    const request = {
      provider_id: provider,
      capability: cap,
      reference_id: reference.id,
      view,
      parameters,
      ...(parent ? { parent_proposal_id: parent } : {}),
      ...(supersedes ? { supersedes } : {}),
    };
    const first = await client.api.post<CVJob>(base + "/cv-jobs", {
      expected_revision: snapshot.revision,
      lease_id: client.state.lease,
      request,
    });
    jobs.current.add(first.job_id);
    let value = first;
    try {
      while (value.activity !== "FINISHED") {
        if (
          !mounted.current ||
          pinned !== token.current ||
          epoch !== generation.current
        ) {
          await client.api.post(
            base + "/cv-jobs/" + value.job_id + "/cancel",
            {},
          );
          throw new Error("CV request cancelled or source context changed");
        }
        await new Promise((r) => setTimeout(r, cap === "smart_edge" ? 20 : 80));
        value = await client.api.call<CVJob>(base + "/cv-jobs/" + value.job_id);
        if (mounted.current) setJob(value);
      }
      if (value.result !== "SUCCEEDED" || !value.proposal_id)
        throw new Error(value.error || "CV job " + value.result);
      const p = await client.api.call<CVProposal>(
        base + "/cv-proposals/" + value.proposal_id,
      );
      if (
        !mounted.current ||
        pinned !== token.current ||
        epoch !== generation.current
      )
        throw new Error("Stale CV result suppressed");
      return p;
    } finally {
      jobs.current.delete(first.job_id);
    }
  }
  const parameters = () => ({
    preset,
    threshold,
    search_radius: radius,
    edge_attraction: attraction,
    smoothness,
    minimum_contrast: contrast,
    tolerance,
    roi,
  });
  function dirty() {
    cancelAll();
    setEdge(null);
    setPreview([]);
    setAnchor(null);
    setTrace(null);
    trail.current = [];
    if (proposal?.status === "ACTIVE") {
      setProposal({ ...proposal, status: "STALE" });
      void client.api
        .post(base + "/cv-proposals/" + proposal.proposal_id + "/stale", {})
        .catch((e) => setError(e.message));
    }
  }
  async function execute(
    cap: string,
    extra: Record<string, unknown> = {},
    supersedes?: string,
  ) {
    setBusy(true);
    setError("");
    try {
      const p = await run(
        cap,
        { ...parameters(), ...extra },
        undefined,
        supersedes,
      );
      choose(p);
      if (!p.components.length)
        setError(
          p.warnings.join(" · ") ||
            "EMPTY: no candidates. Manual tools remain available.",
        );
      return p;
    } catch (e) {
      if (mounted.current) setError((e as Error).message);
      return null;
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  async function edgeMap() {
    setBusy(true);
    setError("");
    try {
      const p = await run("detect_edges", parameters());
      setEdge(p);
      setEdgeVisible(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function schedulePreview() {
    if (previewRunning.current || previewTimer.current || busy || !anchor)
      return;
    const epoch = generation.current;
    previewTimer.current = setTimeout(async () => {
      previewTimer.current = null;
      if (
        epoch !== generation.current ||
        !mounted.current ||
        latest.current.busy
      )
        return;
      const s = latest.current;
      if (s.trail.length < 2) return;
      previewRunning.current = true;
      const requestNumber = ++lastPreviewRequest.current,
        began = pointerAt.current || performance.now();
      const endpoint = JSON.stringify(s.trail.at(-1));
      try {
        const directed = s.trail.map((v: number[]) => [...v]);
        const p = await s.run(
          "smart_edge",
          { ...s.parameters(), trajectory: directed },
          s.trace?.proposal_id,
        );
        if (
          epoch === generation.current &&
          requestNumber === lastPreviewRequest.current &&
          p.status === "ACTIVE"
        ) {
          setPreview(
            p.components[0]?.preview_points || p.components[0]?.points || [],
          );
          requestAnimationFrame(() =>
            requestAnimationFrame(() => {
              if (mounted.current && epoch === generation.current)
                setPreviewTimes((v) => [
                  ...v.slice(-255),
                  performance.now() - began,
                ]);
            }),
          );
        }
      } catch (e) {
        if (epoch === generation.current && mounted.current)
          setError((e as Error).message);
      } finally {
        if (epoch === generation.current) {
          previewRunning.current = false;
          if (endpoint !== JSON.stringify(latest.current.trail.at(-1)))
            latest.current.schedulePreview();
        }
      }
    }, 80);
  }
  async function down(point: number[]) {
    if (!available || busy || !context) return;
    if (tool === "smart_edge") {
      if (!anchor) {
        setAnchor(point);
        trail.current = [point];
        setPreview([point]);
        return;
      }
      const started = performance.now(),
        directed = [trail.current[0], ...trail.current.slice(-126), point];
      cancelAll();
      setBusy(true);
      setError("");
      try {
        const segment = await run(
          "smart_edge",
          { ...parameters(), trajectory: directed },
          trace?.proposal_id,
        );
        if (!segment.components.length)
          throw new Error(
            segment.warnings.join(" · ") || "No directed segment found",
          );
        const combined = trace
          ? await client.api.post<CVProposal>(base + "/cv-traces", {
              expected_revision: snapshot.revision,
              proposal_ids: [trace.proposal_id, segment.proposal_id],
            })
          : segment;
        setTrace(combined);
        choose(combined);
        const points = combined.components[0].original_points!;
        const end = points.at(-1)!;
        setAnchor(end);
        trail.current = [end];
        setPreview([]);
        requestAnimationFrame(() =>
          requestAnimationFrame(() => {
            if (mounted.current)
              setCommitTimes((v) => [
                ...v.slice(-255),
                performance.now() - started,
              ]);
          }),
        );
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy(false);
      }
      return;
    }
    drag.current = [point];
    setBox(undefined);
  }
  function move(point: number[], dragging: boolean) {
    if (tool === "smart_edge" && anchor && !busy) {
      pointerAt.current = performance.now();
      if (trail.current.length < 128) trail.current.push(point);
      else
        trail.current = [trail.current[0], ...trail.current.slice(-125), point];
      schedulePreview();
    } else if (dragging && !busy) {
      if (tool === "foreground" || tool === "background") {
        if (drag.current.length < 128) drag.current.push(point);
        setPreview([...drag.current]);
      } else if (drag.current[0] && context)
        setBox(roundBox(drag.current[0], point, context.crop));
    }
  }
  async function up(point: number[]) {
    if (tool === "smart_edge" || busy || !drag.current[0] || !context) return;
    if (tool === "foreground" || tool === "background") {
      const next = [
        ...strokes,
        {
          label:
            tool === "foreground"
              ? ("foreground" as const)
              : ("background" as const),
          points: [...drag.current, point].slice(0, 128),
          radius: brushRadius,
        },
      ];
      drag.current = [];
      setPreview([]);
      setStrokes(next);
      await execute(
        "segment_object",
        { strokes: next },
        proposal?.status === "ACTIVE" ? proposal.proposal_id : undefined,
      );
    } else {
      const next = roundBox(drag.current[0], point, context.crop);
      drag.current = [];
      setBox(next);
      if (next[2] - next[0] < 8 || next[3] - next[1] < 8) {
        setError(
          "Drag an ROI at least 8 × 8 source pixels, or enter ROI coordinates.",
        );
        return;
      }
      setRoi(next);
      setStrokes([]);
      await execute(
        capability(tool),
        { roi: next, strokes: [] },
        proposal?.status === "ACTIVE" ? proposal.proposal_id : undefined,
      );
    }
  }
  latest.current = {
    busy,
    run,
    parameters,
    get trail() {
      return trail.current;
    },
    trace,
    down,
    move,
    up,
    schedulePreview,
  };
  const callbacks = useMemo(
    () => ({
      onDown: (p: number[]) => void latest.current.down(p),
      onMove: (p: number[], d: boolean) => latest.current.move(p, d),
      onUp: (p: number[]) => void latest.current.up(p),
    }),
    [],
  );
  const canvas = useMemo<AssistCanvas>(
    () => ({
      sourceId: reference.id,
      view,
      crop: context?.crop,
      active: available && context !== null && tool !== "inspect",
      visible,
      opacity,
      components: proposal?.components || [],
      selected,
      original,
      preview,
      box,
      ...callbacks,
      rasters: [
        ...(edgeVisible &&
        edge?.raster_bounds &&
        edge.source_reference_id === reference.id
          ? [
              {
                url: `/api/v1${base}/cv-proposals/${edge.proposal_id}/rasters/edges`,
                bounds: edge.raster_bounds,
                opacity: edgeOpacity,
              },
            ]
          : []),
        ...(maskVisible &&
        proposal?.rasters.includes("mask") &&
        proposal.raster_bounds
          ? [
              {
                url: `/api/v1${base}/cv-proposals/${proposal.proposal_id}/rasters/mask`,
                bounds: proposal.raster_bounds,
                opacity: 0.45,
              },
            ]
          : []),
      ],
    }),
    [
      reference.id,
      view,
      context,
      available,
      tool,
      visible,
      opacity,
      proposal,
      selected,
      original,
      preview,
      box,
      edgeVisible,
      edge,
      edgeOpacity,
      maskVisible,
    ],
  );
  useEffect(() => {
    onCanvas(canvas);
  }, [canvas, onCanvas]);
  async function edit(action: string, extra: Record<string, unknown> = {}) {
    if (!proposal || !component) return;
    setBusy(true);
    setError("");
    try {
      const p = await client.api.post<CVProposal>(
        base + "/cv-proposals/" + proposal.proposal_id + "/edit",
        {
          edit: {
            component_id: component.id,
            proposal_revision: proposal.proposal_revision,
            action,
            ...extra,
          },
        },
      );
      setProposal(p);
      setSelected([component.id]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function decide(action: "accept" | "reject") {
    if (!proposal || !selected.length) return;
    setBusy(true);
    setError("");
    try {
      if (action === "accept") {
        if (
          await client.run(`cv-proposals/${proposal.proposal_id}/accept`, {
            proposal_revision: proposal.proposal_revision,
            component_ids: selected,
            semantic_roles: Object.fromEntries(
              selected.map((id) => [id, role]),
            ),
            confirm_observed: verified,
          })
        ) {
          setProposal(
            await client.api.call<CVProposal>(
              base + "/cv-proposals/" + proposal.proposal_id,
            ),
          );
          setTool("inspect");
        } else
          throw new Error(client.state.error?.message || "Acceptance rejected");
      } else {
        setProposal(
          await client.api.post<CVProposal>(
            base + "/cv-proposals/" + proposal.proposal_id + "/reject",
            { component_ids: selected },
          ),
        );
        setTrace(null);
        setAnchor(null);
        setPreview([]);
        trail.current = [];
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const nums = (values: number[]) => [...values].sort((a, b) => a - b);
  const stats = (v: number[]) =>
    v.length
      ? `${nums(v)[Math.floor(v.length * 0.5)].toFixed(1)} / ${nums(v)[Math.min(v.length - 1, Math.floor(v.length * 0.95))].toFixed(1)} ms`
      : "not measured";
  return (
    <div
      className="cv-panel"
      data-testid="cv-panel"
      data-proposal-status={proposal?.status || "NONE"}
      data-proposal-id={proposal?.proposal_id || ""}
      data-busy={String(busy)}
      data-cv-tool={tool}
      data-mask-strokes={strokes.length}
      data-preview-times={JSON.stringify(previewTimes)}
      data-commit-times={JSON.stringify(commitTimes)}
      data-preview-samples={previewTimes.length}
      data-commit-samples={commitTimes.length}
    >
      <div className="cv-heading">
        <h2>Annotation assistance</h2>
        <button onClick={props.onExit}>Manual tools</button>
      </div>
      <p className="cv-contract">
        CV PROPOSAL ≠ source observation ≠ world geometry. Only ACCEPT writes
        source observations.
      </p>
      <label>
        Provider
        <select
          aria-label="CV provider"
          value={provider}
          onChange={(e) => {
            dirty();
            setProvider(e.target.value);
          }}
        >
          {providers.map((p) => (
            <option key={p.provider_id} value={p.provider_id}>
              {p.name || p.provider_id} · {p.provider_version}
              {p.available ? "" : " · unavailable"}
            </option>
          ))}
        </select>
      </label>
      {!available && (
        <p role="status">
          Provider unavailable. Install the optional Studio cv extra or use
          manual tools. No automatic fallback or downloads.
        </p>
      )}
      <div className="cv-tool-grid">
        {(
          [
            "smart_edge",
            "magic_select",
            "detect_wheels",
            "trace_contour",
          ] as AssistTool[]
        ).map((t) => (
          <button
            key={t}
            disabled={
              !available ||
              busy ||
              !providers
                .find((p) => p.provider_id === provider)
                ?.capabilities.includes(capability(t))
            }
            className={tool === t ? "active" : ""}
            onClick={() => {
              cancelAll();
              setTool(t);
              setAnchor(null);
              setTrace(null);
              setPreview([]);
            }}
          >
            {
              {
                smart_edge: "Smart Edge",
                magic_select: "Magic Select",
                detect_wheels: "Detect Wheels",
                trace_contour: "Trace Contour",
              }[t as "smart_edge"]
            }
          </button>
        ))}
      </div>
      <p role="status">
        {tool === "smart_edge"
          ? "Click a start, follow the feature, click to commit segments, then Finish trace."
          : tool === "foreground" || tool === "background"
            ? "Brush source pixels to refine the proposal mask."
            : "Drag a source ROI or enter its pixel bounds below. Proposals stay in this view."}
      </p>
      {tool === "smart_edge" && (
        <button
          disabled={!trace || busy}
          onClick={() => {
            cancelAll();
            setTool("inspect");
            setAnchor(null);
            setPreview([]);
          }}
        >
          Finish trace
        </button>
      )}
      <label>
        Edge preset
        <select
          aria-label="Edge preset"
          value={preset}
          onChange={(e) => {
            dirty();
            setPreset(e.target.value);
            setThreshold(
              { Weak: 64, Normal: 140, Strong: 220 }[
                e.target.value as "Normal"
              ],
            );
          }}
        >
          {["Weak", "Normal", "Strong"].map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
      </label>
      <details>
        <summary>ROI / Advanced</summary>
        <div className="cv-coordinates">
          {["left", "top", "right", "bottom"].map((v, i) => (
            <label key={v}>
              {v}
              <input
                aria-label={"CV ROI " + v}
                type="number"
                value={roi[i]}
                onChange={(e) => {
                  dirty();
                  setRoi(
                    roi.map((n, j) => (i === j ? Number(e.target.value) : n)),
                  );
                }}
              />
            </label>
          ))}
        </div>
        <label>
          Search radius
          <input
            aria-label="Smart Edge radius"
            type="number"
            min="4"
            max="96"
            value={radius}
            onChange={(e) => {
              dirty();
              setRadius(Number(e.target.value));
            }}
          />
        </label>
        <label>
          Edge attraction
          <input
            type="number"
            min="0"
            max="20"
            value={attraction}
            onChange={(e) => {
              dirty();
              setAttraction(Number(e.target.value));
            }}
          />
        </label>
        <label>
          Smoothness / direction continuity
          <input
            type="number"
            min="0"
            max="5"
            step=".1"
            value={smoothness}
            onChange={(e) => {
              dirty();
              setSmoothness(Number(e.target.value));
            }}
          />
        </label>
        <label>
          Minimum contrast
          <input
            type="number"
            min="0"
            max="255"
            value={contrast}
            onChange={(e) => {
              dirty();
              setContrast(Number(e.target.value));
            }}
          />
        </label>
        <button
          disabled={
            !available || busy || tool === "smart_edge" || tool === "inspect"
          }
          onClick={() =>
            void execute(
              capability(tool),
              { strokes },
              proposal?.status === "ACTIVE" ? proposal.proposal_id : undefined,
            )
          }
        >
          Run in ROI
        </button>
      </details>
      <fieldset>
        <legend>CV Proposals · transient layer</legend>
        <label>
          <input
            type="checkbox"
            checked={visible}
            onChange={(e) => setVisible(e.target.checked)}
          />
          Visible · dashed
        </label>
        <label>
          Opacity
          <input
            aria-label="CV Proposals opacity"
            type="range"
            min="0"
            max="1"
            step=".05"
            value={opacity}
            onChange={(e) => setOpacity(Number(e.target.value))}
          />
        </label>
        <label>
          <input
            type="checkbox"
            checked={original}
            onChange={(e) => setOriginal(e.target.checked)}
          />
          Overlay original contour
        </label>
        <label>
          <input
            type="checkbox"
            checked={maskVisible}
            onChange={(e) => setMaskVisible(e.target.checked)}
          />
          Mask preview
        </label>
      </fieldset>
      <fieldset>
        <legend>Edge Map · diagnostic only</legend>
        <label>
          <input
            aria-label="Edge Map visible"
            type="checkbox"
            checked={edgeVisible}
            onChange={(e) => setEdgeVisible(e.target.checked)}
          />
          Visible
        </label>
        <label>
          Opacity
          <input
            aria-label="Edge Map opacity"
            type="range"
            min="0"
            max="1"
            step=".05"
            value={edgeOpacity}
            onChange={(e) => setEdgeOpacity(Number(e.target.value))}
          />
        </label>
        <label>
          Threshold
          <input
            aria-label="Edge Map threshold"
            type="number"
            min="1"
            max="255"
            value={threshold}
            onChange={(e) => {
              dirty();
              setThreshold(Number(e.target.value));
            }}
          />
        </label>
        <button disabled={!available || busy} onClick={() => void edgeMap()}>
          Update edge map
        </button>
      </fieldset>
      {proposal?.rasters.includes("mask") && (
        <fieldset>
          <legend>Magic Select corrections</legend>
          <button
            disabled={busy || !active}
            onClick={() => setTool("foreground")}
          >
            Foreground / Add region
          </button>
          <button
            disabled={busy || !active}
            onClick={() => setTool("background")}
          >
            Background / Remove region
          </button>
          <label>
            Brush radius px
            <input
              aria-label="Mask brush radius"
              type="number"
              min="1"
              max="64"
              value={brushRadius}
              onChange={(e) => setBrushRadius(Number(e.target.value))}
            />
          </label>
          <span>
            {strokes.length} correction strokes · immutable image unchanged
          </span>
        </fieldset>
      )}
      {job && (
        <p role="status">
          CV job: {job.activity} ·{" "}
          {job.result || `${Math.round(job.progress * 100)}%`}
        </p>
      )}
      {(busy || jobs.current.size > 0) && (
        <button
          onClick={() => {
            cancelAll();
            setBusy(false);
            setError("Cancellation requested; manual tools remain available.");
          }}
        >
          Cancel CV job
        </button>
      )}
      {error && (
        <p className="cv-error" role="alert">
          {error}
        </p>
      )}
      {proposal && (
        <section aria-label="Proposal inspector">
          <h3>Proposal inspector · {proposal.status}</h3>
          <p>
            {proposal.provider_id} {proposal.provider_version} ·{" "}
            {proposal.capability}
          </p>
          <p>
            Source revision <code>{proposal.source_revision.slice(0, 12)}</code>{" "}
            · crop {proposal.crop.join(", ")} · {proposal.elapsed_ms.toFixed(1)}{" "}
            ms{proposal.cache_hit ? " · cache hit" : ""}
          </p>
          {proposal.warnings.map((v) => (
            <p key={v}>{v}</p>
          ))}
          <details>
            <summary>Parameters / input hash</summary>
            <pre>{JSON.stringify(proposal.parameters, null, 2)}</pre>
            <code>{proposal.created_input_hash}</code>
          </details>
          <div className="cv-candidates">
            {proposal.components.map((c) => (
              <label
                key={c.id}
                className={
                  "cv-candidate " + (selected.includes(c.id) ? "selected" : "")
                }
              >
                <input
                  aria-label={"Select CV " + c.id}
                  type="checkbox"
                  checked={selected.includes(c.id)}
                  onChange={(e) =>
                    setSelected(
                      e.target.checked
                        ? [...selected, c.id]
                        : selected.filter((id) => id !== c.id),
                    )
                  }
                />
                <span>
                  {c.id} · {c.kind} · {c.status}
                  <small>
                    {c.semantic_role} · {c.points?.length || "circle"} points
                    {c.score !== null
                      ? ` · score ${c.score.toFixed(3)} (geometric only)`
                      : ""}
                  </small>
                </span>
              </label>
            ))}
          </div>
          {component?.fit && (
            <dl className="cv-fit-evidence">
              <dt>Max / RMS deviation px</dt>
              <dd>
                {component.fit.max_deviation_px.toFixed(3)} /{" "}
                {component.fit.rms_deviation_px.toFixed(3)}
              </dd>
              <dt>Continuous upper bound px</dt>
              <dd>
                {component.fit.certified_max_deviation_px.toFixed(3)} ≤{" "}
                {component.fit.tolerance_px}
              </dd>
              <dt>Control points / original samples</dt>
              <dd>
                {component.fit.control_point_count} /{" "}
                {component.fit.original_sample_count}
              </dd>
            </dl>
          )}
          <label>
            Semantic role
            <select
              aria-label="CV semantic role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option>UNKNOWN</option>
              {snapshot.roles.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </label>
          <label>
            <input
              aria-label="CV source pixels verified"
              type="checkbox"
              checked={verified}
              onChange={(e) => setVerified(e.target.checked)}
            />
            I verified these source pixels. Otherwise accepted evidence remains
            INFERRED.
          </label>
          <div className="cv-actions">
            <button
              disabled={
                busy ||
                !active ||
                !selected.length ||
                role === "UNKNOWN" ||
                !client.writable ||
                tool === "smart_edge"
              }
              onClick={() => void decide("accept")}
            >
              ACCEPT selected
            </button>
            <button
              disabled={busy || !active || !selected.length}
              onClick={() => void decide("reject")}
            >
              REJECT selected
            </button>
            <button
              disabled={!available || busy}
              onClick={() =>
                void execute(
                  proposal.capability,
                  {
                    ...(proposal.parameters.trajectory
                      ? { trajectory: proposal.parameters.trajectory }
                      : {}),
                    strokes,
                  },
                  proposal.status === "ACTIVE"
                    ? proposal.proposal_id
                    : undefined,
                )
              }
            >
              RERUN
            </button>
          </div>
          {component && component.kind !== "circle" && (
            <details open>
              <summary>EDIT / contour / fitting</summary>
              <p>
                Fit error refers to the working contour. The original dense
                contour stays available for comparison.
              </p>
              <button
                disabled={!active || busy}
                onClick={() => void edit("reverse")}
              >
                Reverse direction
              </button>
              <button
                disabled={!active || busy}
                onClick={() => void edit(component.closed ? "open" : "close")}
              >
                {component.closed ? "Open contour" : "Close contour"}
              </button>
              <div className="cv-coordinates">
                <label>
                  Trim start
                  <input
                    aria-label="CV trim start"
                    type="number"
                    value={trimStart}
                    onChange={(e) => setTrimStart(Number(e.target.value))}
                  />
                </label>
                <label>
                  Trim end
                  <input
                    aria-label="CV trim end"
                    type="number"
                    value={trimEnd}
                    onChange={(e) => setTrimEnd(Number(e.target.value))}
                  />
                </label>
              </div>
              <button
                disabled={!active || busy}
                onClick={() =>
                  void edit("trim", { start: trimStart, end: trimEnd })
                }
              >
                Trim contour
              </button>
              <label>
                Deviation tolerance px
                <input
                  aria-label="CV fit tolerance"
                  type="number"
                  min=".05"
                  max="32"
                  step=".1"
                  value={tolerance}
                  onChange={(e) => setTolerance(Number(e.target.value))}
                />
              </label>
              <label>
                Maximum control points
                <input
                  aria-label="CV maximum points"
                  type="number"
                  min="2"
                  max="1024"
                  value={maximum}
                  onChange={(e) => setMaximum(Number(e.target.value))}
                />
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={corners}
                  onChange={(e) => setCorners(e.target.checked)}
                />
                Preserve important corners
              </label>
              <label>
                <input
                  aria-label="CV fit spline"
                  type="checkbox"
                  checked={spline}
                  onChange={(e) => setSpline(e.target.checked)}
                />
                Fit spline proposal
              </label>
              <button
                disabled={!active || busy}
                onClick={() =>
                  void edit("fit", {
                    tolerance,
                    max_points: maximum,
                    preserve_corners: corners,
                    spline,
                  })
                }
              >
                Simplify / Fit proposal
              </button>
              <div className="cv-coordinates">
                <label>
                  Point index
                  <input
                    aria-label="CV edit point index"
                    type="number"
                    value={editIndex}
                    onChange={(e) => setEditIndex(Number(e.target.value))}
                  />
                </label>
                {["X", "Y"].map((v, i) => (
                  <label key={v}>
                    {v} px
                    <input
                      aria-label={"CV edit " + v}
                      type="number"
                      value={editXY[i]}
                      onChange={(e) =>
                        setEditXY(
                          editXY.map((s, j) => (i === j ? e.target.value : s)),
                        )
                      }
                    />
                  </label>
                ))}
              </div>
              <button
                disabled={!active || busy}
                onClick={() =>
                  void edit("move_point", {
                    index: editIndex,
                    pixel: editXY.map(Number),
                  })
                }
              >
                EDIT proposal point
              </button>
            </details>
          )}
        </section>
      )}
      <details>
        <summary>Measured interaction timings</summary>
        <p>Smart Edge preview p50 / p95: {stats(previewTimes)}</p>
        <p>Segment commit p50 / p95: {stats(commitTimes)}</p>
        <p>
          Includes local request and proposal display; no canonical save until
          ACCEPT.
        </p>
      </details>
    </div>
  );
}
