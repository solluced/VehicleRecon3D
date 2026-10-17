import {
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  lazy,
  Suspense,
} from "react";
import { API, EditorClient, type APIError } from "./api";
import { SourceCanvas, type Tool } from "./Canvas";
import type { AssistCanvas, AssistTool } from "./cv-types";
const CVPanel = lazy(() =>
  import("./CVPanel").then((m) => ({ default: m.CVPanel })),
);
const MultiWorkspace = lazy(() =>
  import("./MultiWorkspace").then((m) => ({ default: m.MultiWorkspace })),
);
const RectificationWorkspace = lazy(() =>
  import("./RectificationWorkspace").then((m) => ({
    default: m.RectificationWorkspace,
  })),
);
import { Properties, RolePicker, SchemaField, Settings } from "./Forms";
import {
  category,
  activeReference,
  defaults,
  editable,
  layerFor,
  type AuthoringCommand,
  type Camera,
  type Observation,
  type Preferences,
  type ProjectEntry,
  type Ready,
  type Reference,
  type Schema,
  type Selection,
  type Snapshot,
  type View,
} from "./types";
const id = (prefix: string) =>
  prefix + "_" + crypto.randomUUID().replaceAll("-", "");
const api = new API(),
  client = new EditorClient(api);
export default function App() {
  const [ready, setReady] = useState(false),
    [fatal, setFatal] = useState(""),
    [projects, setProjects] = useState<ProjectEntry[]>([]),
    [roots, setRoots] = useState<
      { id: string; label: string; revision: string }[]
    >([]),
    [schemas, setSchemas] = useState<Record<string, Schema>>({}),
    [profiles, setProfiles] = useState<string[]>([]),
    [page, setPage] = useState<"home" | "editor">("home");
  const state = useSyncExternalStore(client.subscribe, client.getSnapshot),
    snapshot = state.snapshot;
  const [selection, setSelection] = useState<Selection>(null),
    [tool, setTool] = useState<Tool>("select"),
    [role, setRole] = useState("roof"),
    [draft, setDraft] = useState<number[][]>([]),
    [prefs, setPrefs] = useState<Preferences>({
      layers: defaults,
      active_view: "side",
    }),
    [inspector, setInspector] = useState<"properties" | "settings">(
      "properties",
    );
  const [eventsStatus, setEventsStatus] = useState("Connecting"),
    [showReady, setShowReady] = useState(true),
    [multi, setMulti] = useState(false),
    [rectification, setRectification] = useState(false);
  const pendingPrefs = useRef<ReturnType<typeof setTimeout> | null>(null),
    prefsRef = useRef(prefs);
  const [cvOpen, setCVOpen] = useState(false),
    [cvTool, setCVTool] = useState<AssistTool>("smart_edge"),
    [cvActivation, setCVActivation] = useState(0),
    [assist, setAssist] = useState<AssistCanvas | undefined>();
  prefsRef.current = prefs;
  async function list() {
    const [p, r] = await Promise.all([
      api.call<ProjectEntry[]>("/projects"),
      api.call<typeof roots>("/roots"),
    ]);
    setProjects(p);
    setRoots(r);
  }
  useEffect(() => {
    void (async () => {
      try {
        await api.bootstrap();
        await list();
        const s = await api.call<{
          schemas: Record<string, Schema>;
          profiles: Record<string, unknown>;
        }>("/schemas");
        setSchemas(s.schemas);
        setProfiles(Object.keys(s.profiles));
        setReady(true);
      } catch (e) {
        setFatal((e as Error).message);
      }
    })();
  }, []);
  useEffect(() => {
    if (!ready) return;
    const es = new EventSource("/api/v1/events?tab_id=" + api.tab);
    es.onopen = () => setEventsStatus("Live");
    es.onerror = () => setEventsStatus("Reconnecting");
    const changed = (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      if (
        client.state.snapshot?.id === data.project_id &&
        data.actor_tab !== api.tab
      )
        void client.reconcile();
    };
    for (const kind of ["project_changed", "revision_changed", "conflict"])
      es.addEventListener(kind, changed);
    es.addEventListener("resync", () => {
      setEventsStatus("Live");
      void client.reconcile();
    });
    return () => es.close();
  }, [ready]);
  useEffect(() => {
    if (!snapshot || !state.lease) return;
    const timer = setInterval(() => void client.renew(), 15000);
    return () => clearInterval(timer);
  }, [snapshot?.id, state.lease]);
  async function open(p: ProjectEntry) {
    if (!(await client.open(p.id))) return;
    const s = client.state.snapshot!;
    setPrefs({
      ...s.preferences,
      layers: { ...defaults, ...s.preferences.layers },
      active_view: s.preferences.active_view || "side",
    });
    setSelection(null);
    setRectification(false);
    setDraft([]);
    setPage("editor");
    setRole(s.roles?.includes("roof") ? "roof" : s.roles?.[0] || "roof");
  }
  function preference(patch: Partial<Preferences>) {
    setPrefs((p) => ({ ...p, ...patch }));
    if (pendingPrefs.current) clearTimeout(pendingPrefs.current);
    pendingPrefs.current = setTimeout(() => {
      if (client.writable) void client.preferences(prefsRef.current);
    }, 900);
  }
  async function home() {
    if (pendingPrefs.current) clearTimeout(pendingPrefs.current);
    if (client.writable) {
      await client.preferences(prefsRef.current);
      const s = client.state.snapshot!;
      await api.post("/projects/" + s.id + "/release", {
        expected_revision: s.revision,
        lease_id: client.state.lease,
      });
    }
    client.set({ snapshot: null, lease: "" });
    setPage("home");
    await list();
  }
  const reference = activeReference(snapshot, prefs);
  const selected = snapshot?.observations.find(
    (o) => o.id === selection?.entity,
  );
  const view = prefs.active_view || "side";
  const canEdit = client.writable && (!selected || editable(selected, prefs));
  function choose(s: Selection) {
    setSelection(s);
    setInspector("properties");
  }
  async function add(pixel: number[]) {
    if (!client.writable || !snapshot || !reference) return;
    const layer = tool === "point" ? "observations" : "curves";
    if (!prefs.layers?.[layer]?.visible || prefs.layers[layer].locked) return;
    if (tool === "point") {
      await client.commands([
        { type: "AddObservation", view, observation: base("point", pixel) },
      ]);
    } else if (
      tool === "polyline" ||
      tool === "spline" ||
      (tool === "measure" && draft.length < 2)
    )
      setDraft((d) => [...d, pixel]);
    else if (tool === "insert" && selected && "points" in selected) {
      const after = selection?.point || selected.points.at(-1)!.id;
      await client.commands([
        {
          type: "AddSplinePoint",
          target: "observation",
          entity_id: selected.id,
          after_point_id: after,
          point_id: id("knot"),
          point: pixel,
        },
      ]);
    }
  }
  function base(
    kind: "point" | "polyline" | "spline" | "axis",
    pixel?: number[],
  ): Observation {
    const common = {
      id: id("obs"),
      view,
      semantic_role: role,
      reference_id: reference!.role,
      source_sha256: reference!.sha256,
      crop_id: snapshot!.views[view]?.crop_id[reference!.role],
      revision: 1,
      provenance: {
        type: "measured" as const,
        method: "Manual source annotation",
      },
      uncertainty_px: 1,
      visibility: "observed" as const,
      measured: true,
    };
    if (kind === "point") return { ...common, kind, pixel: pixel! };
    const points = draft.map((pixel, i) => {
      const previous = draft[Math.max(0, i - 1)],
        next = draft[Math.min(draft.length - 1, i + 1)],
        tangent = [(next[0] - previous[0]) / 6, (next[1] - previous[1]) / 6];
      return {
        id: id("knot"),
        pixel,
        ...(kind === "spline"
          ? {
              left: pixel.map((p, a) => p - tangent[a]),
              right: pixel.map((p, a) => p + tangent[a]),
            }
          : {}),
      };
    });
    return { ...common, kind, points };
  }
  async function finish() {
    if (
      draft.length < 2 ||
      !(tool === "polyline" || tool === "spline" || tool === "measure")
    )
      return;
    const observation = base(tool === "measure" ? "axis" : tool);
    if (
      await client.commands([{ type: "AddObservation", view, observation }])
    ) {
      setDraft([]);
      setTool("select");
      choose({ entity: observation.id });
    }
  }
  async function remove() {
    if (!selected || !canEdit) return;
    const command: AuthoringCommand =
      selection?.point && "points" in selected
        ? {
            type: "DeleteSplinePoint",
            target: "observation",
            entity_id: selected.id,
            point_id: selection.point,
          }
        : { type: "DeleteObservation", observation_id: selected.id };
    if (await client.commands([command])) choose(null);
  }
  async function move(selection: NonNullable<Selection>, pixel: number[]) {
    return client.commands([
      selection.point
        ? {
            type: "MoveSplinePoint",
            target: "observation",
            entity_id: selection.entity,
            point_id: selection.point,
            point: pixel,
          }
        : { type: "MoveObservation", observation_id: selection.entity, pixel },
    ]);
  }
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).matches("input,textarea,select")) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        void client.run(e.shiftKey ? "redo" : "undo");
      } else if (multi || cvOpen || rectification) return;
      else if (e.key === "Enter") void finish();
      else if (e.key === "Delete" || e.key === "Backspace") {
        e.preventDefault();
        void remove();
      } else if (e.key === "Escape") {
        setDraft([]);
        setTool("select");
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  });
  const counts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const o of snapshot?.observations || [])
      m[layerFor(o, prefs)] = (m[layerFor(o, prefs)] || 0) + 1;
    return m;
  }, [snapshot?.observations, prefs.assignments]);
  if (fatal)
    return (
      <main className="welcome">
        <div className="brand">
          VR <span>VehicleRecon Studio</span>
        </div>
        <h1>Local session unavailable</h1>
        <p>{fatal}</p>
        <p>
          Launch Studio again from the terminal to open a secure local session.
        </p>
      </main>
    );
  if (!ready)
    return (
      <main className="welcome">
        <h1>Opening your workspace…</h1>
      </main>
    );
  return (
    <div className="app">
      <header className="app-header">
        <button
          className="brand"
          onClick={() => void home()}
          aria-label="Project home"
        >
          <b>VR</b>
          <span>
            VehicleRecon <strong>Studio</strong>
          </span>
        </button>
        <span className="phase-label">
          RECONSTRUCTION WORKSPACE <b>0.4</b>
        </span>
        <span className="connection">
          <i />
          {eventsStatus}
        </span>
      </header>
      {page === "home" || !snapshot ? (
        <main className="home">
          {state.error && (
            <div className="error-banner" role="alert">
              {state.error.message}
              <button onClick={() => client.set({ error: null })}>
                Dismiss
              </button>
            </div>
          )}
          <div className="home-heading">
            <div className="eyebrow">YOUR WORKSPACE</div>
            <h1>Start with the source.</h1>
            <p>
              Mark what you can observe. Keep what you don’t know unresolved.
            </p>
          </div>
          <div className="home-columns">
            <section>
              <div className="section-heading">
                <h2>Projects</h2>
                <button onClick={() => void list()}>Refresh</button>
              </div>
              <div className="project-list">
                {projects.map((p) => (
                  <button
                    className="project-card"
                    key={p.id}
                    onClick={() => void open(p)}
                    disabled={!p.project}
                  >
                    <span className="project-icon">
                      {p.read_only ? "◇" : "▱"}
                    </span>
                    <span>
                      <strong>
                        {p.project?.asset_name || "Unavailable project"}
                      </strong>
                      <small>
                        {p.project?.vehicle_profile} ·{" "}
                        {p.read_only
                          ? "LEGACY v" + p.version + " · READ ONLY"
                          : "v2 · " + (p.project?.authoring_state || "DRAFT")}
                      </small>
                      <code>{p.revision?.slice(0, 12)}</code>
                      <small>
                        {p.version === 2
                          ? `Surfaces: ${(p.readiness?.surfaces as Ready)?.state || "status unavailable"}`
                          : "Legacy authoring · read only"}
                      </small>
                    </span>
                    <span className="card-arrow">↗</span>
                  </button>
                ))}
                {!projects.length && (
                  <div className="empty-card">
                    No projects yet. Create a draft to begin.
                  </div>
                )}
              </div>
            </section>
            <NewProject
              roots={roots}
              profiles={profiles}
              api={api}
              onCreated={async (p) => {
                await list();
                await open(p);
              }}
            />
          </div>
        </main>
      ) : (
        <>
          <div className="project-bar">
            <button onClick={() => void home()} className="back">
              ← Projects
            </button>
            <strong>{snapshot.project.asset_name}</strong>
            <span className="badge">
              {snapshot.read_only
                ? "LEGACY v1 · READ ONLY"
                : snapshot.project.authoring_state}
            </span>
            <code title={snapshot.revision}>
              {snapshot.revision.slice(0, 12)}
            </code>
            <span
              className={"save-state " + (state.conflict ? "conflict" : "")}
            >
              {state.conflict
                ? "Conflict"
                : state.busy
                  ? "Saving…"
                  : state.error
                    ? "Error"
                    : "Saved"}
            </span>
            <button onClick={() => void client.reload()}>Reload project</button>
            <button
              aria-pressed={multi}
              onClick={() => {
                setMulti(!multi);
                setRectification(false);
                setCVOpen(false);
                setAssist(undefined);
                setDraft([]);
                setTool("select");
              }}
            >
              {multi ? "Source editor" : "Multi-view / 3D"}
            </button>
            <button
              aria-pressed={rectification}
              onClick={() => {
                setRectification(!rectification);
                setMulti(false);
                setCVOpen(false);
                setAssist(undefined);
                setDraft([]);
                setTool("select");
              }}
            >
              Reference → Rectification
            </button>
          </div>
          {state.error && (
            <div className="error-banner" role="alert">
              <strong>{state.conflict ? "Write stopped. " : ""}</strong>
              {state.error.message}
              <button onClick={() => void client.reload()}>
                Reload canonical state
              </button>
              <details>
                <summary>Technical details</summary>
                <pre>{JSON.stringify(state.error.details, null, 2)}</pre>
              </details>
            </div>
          )}
          {rectification ? (
            <Suspense fallback={<p>Opening rectification workspace…</p>}>
              <RectificationWorkspace snapshot={snapshot} client={client} />
            </Suspense>
          ) : multi ? (
            <Suspense fallback={<p>Opening multi-view workspace…</p>}>
              <MultiWorkspace
                snapshot={snapshot}
                client={client}
                preferences={prefs}
                onPreference={preference}
              />
            </Suspense>
          ) : (
            <div className="editor-grid">
              <aside className="left-panel">
                <div className="section-caption">SOURCE VIEW</div>
                <div className="view-buttons">
                  {(["front", "side", "rear", "top"] as View[]).map((v) => (
                    <button
                      className={v === view ? "active" : ""}
                      key={v}
                      onClick={() => {
                        preference({ active_view: v });
                        setDraft([]);
                      }}
                    >
                      {v.toUpperCase()}
                    </button>
                  ))}
                </div>
                <label>
                  Reference
                  <select
                    aria-label="Reference image"
                    value={reference?.role || ""}
                    onChange={(e) => {
                      preference({ reference_id: e.target.value });
                      setDraft([]);
                      setSelection(null);
                      setTool("select");
                    }}
                  >
                    {snapshot.references.map((r) => (
                      <option key={r.id} value={r.role}>
                        {r.role}
                      </option>
                    ))}
                  </select>
                </label>
                <ImportButton
                  disabled={
                    !client.writable ||
                    snapshot.references.some((r) => r.role === "multiview")
                  }
                  onFile={(file) => void client.import(file)}
                />
                <div className="section-heading">
                  <h3>Layers</h3>
                  <button
                    aria-label="Add display layer"
                    disabled={Object.keys(prefs.layers || {}).length >= 32}
                    onClick={() => {
                      const key = id("layer");
                      preference({
                        layers: {
                          ...prefs.layers,
                          [key]: {
                            name:
                              "Display layer " +
                              Object.keys(prefs.layers || {}).length,
                            category: "observations",
                            visible: true,
                            locked: false,
                            opacity: 1,
                          },
                        },
                      });
                    }}
                  >
                    +
                  </button>
                </div>
                <div className="layers">
                  {Object.entries(prefs.layers || defaults).map(([key, l]) => (
                    <div className="layer" key={key}>
                      <div>
                        <button
                          aria-label={"Toggle " + l.name + " visibility"}
                          aria-pressed={l.visible}
                          onClick={() =>
                            preference({
                              layers: {
                                ...prefs.layers,
                                [key]: { ...l, visible: !l.visible },
                              },
                            })
                          }
                        >
                          {l.visible ? "◉" : "○"}
                        </button>
                        <span>
                          {l.name}
                          <small>
                            {counts[key] ||
                              (key === "image" ? "Immutable" : "0")}
                          </small>
                        </span>
                        <button
                          aria-label={"Toggle " + l.name + " lock"}
                          aria-pressed={l.locked}
                          disabled={key === "image"}
                          onClick={() =>
                            preference({
                              layers: {
                                ...prefs.layers,
                                [key]: { ...l, locked: !l.locked },
                              },
                            })
                          }
                        >
                          {l.locked ? "▣" : "▢"}
                        </button>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        aria-label={l.name + " opacity"}
                        value={l.opacity}
                        onChange={(e) =>
                          preference({
                            layers: {
                              ...prefs.layers,
                              [key]: { ...l, opacity: Number(e.target.value) },
                            },
                          })
                        }
                      />
                    </div>
                  ))}
                </div>
                <div className="section-heading">
                  <h3>Entities</h3>
                  <small>{snapshot.observations.length}</small>
                </div>
                <div className="entity-list">
                  {snapshot.observations
                    .filter(
                      (o) =>
                        o.view === view && o.reference_id === reference?.role,
                    )
                    .slice(0, 150)
                    .map((o) => (
                      <button
                        key={o.id}
                        className={o.id === selection?.entity ? "active" : ""}
                        onClick={() => choose({ entity: o.id })}
                      >
                        <span>{o.kind === "point" ? "•" : "⌁"}</span>
                        <span>
                          {o.semantic_role}
                          <small>{o.id.slice(0, 17)}</small>
                        </span>
                      </button>
                    ))}
                  {snapshot.observations.length > 150 && (
                    <small>
                      First 150 shown. Select any visible control on canvas.
                    </small>
                  )}
                </div>
              </aside>
              <main className="workspace">
                <div className="tool-bar">
                  {(
                    [
                      "select",
                      "pan",
                      "point",
                      "polyline",
                      "spline",
                      "insert",
                    ] as Tool[]
                  ).map((t) => (
                    <button
                      key={t}
                      className={tool === t ? "active" : ""}
                      disabled={
                        !["select", "pan"].includes(t) &&
                        (!client.writable ||
                          (t === "insert" &&
                            !(selected && "points" in selected)))
                      }
                      onClick={() => {
                        setCVOpen(false);
                        setAssist(undefined);
                        setTool(t);
                        setDraft([]);
                      }}
                    >
                      {
                        {
                          select: "↖ Select",
                          pan: "↔ Pan",
                          point: "+ Point",
                          polyline: "⌁ Polyline",
                          spline: "∿ Spline",
                          insert: "+ Knot",
                          measure: "Measure",
                        }[t]
                      }
                    </button>
                  ))}
                  <button
                    disabled={!client.writable}
                    onClick={() => {
                      setCVOpen(false);
                      setAssist(undefined);
                      setTool("point");
                      setDraft([]);
                    }}
                  >
                    Landmark
                  </button>
                  <button
                    disabled={!client.writable}
                    onClick={() => {
                      setCVOpen(false);
                      setAssist(undefined);
                      setTool("measure");
                      setDraft([]);
                    }}
                  >
                    Measure
                  </button>
                  {(
                    [
                      ["smart_edge", "Smart Edge"],
                      ["magic_select", "Magic Select"],
                      ["detect_wheels", "Detect Wheels"],
                      ["trace_contour", "Trace Contour"],
                    ] as [AssistTool, string][]
                  ).map(([t, label]) => (
                    <button
                      key={t}
                      disabled={!reference}
                      className={
                        cvOpen && cvTool === t ? "active cv-tool" : "cv-tool"
                      }
                      onClick={() => {
                        setCVTool(t);
                        setCVActivation((v) => v + 1);
                        setCVOpen(true);
                        setTool("select");
                        setDraft([]);
                        setSelection(null);
                      }}
                    >
                      {label}
                    </button>
                  ))}
                  <span className="tool-separator" />
                  <button
                    aria-label="Undo"
                    disabled={!snapshot.history.undo || !client.writable}
                    onClick={() => void client.run("undo")}
                  >
                    ↶
                  </button>
                  <button
                    aria-label="Redo"
                    disabled={!snapshot.history.redo || !client.writable}
                    onClick={() => void client.run("redo")}
                  >
                    ↷
                  </button>
                  <button
                    disabled={!selected || !canEdit}
                    onClick={() => void remove()}
                  >
                    Delete {selection?.point ? "knot" : "entity"}
                  </button>
                </div>
                {["point", "polyline", "spline", "measure"].includes(tool) && (
                  <div className="creation-bar">
                    <label>
                      New object role
                      <select
                        aria-label="New object role"
                        value={role}
                        onChange={(e) => setRole(e.target.value)}
                      >
                        {snapshot.roles.map((r) => (
                          <option key={r}>{r}</option>
                        ))}
                      </select>
                    </label>
                    {tool !== "point" && (
                      <>
                        <span>
                          {draft.length} knots · Enter to finish
                          {tool === "measure" && draft.length === 2
                            ? ` · ${Math.hypot(draft[1][0] - draft[0][0], draft[1][1] - draft[0][1]).toFixed(2)} source px`
                            : ""}
                        </span>
                        <button
                          disabled={draft.length < 2}
                          onClick={() => void finish()}
                        >
                          Finish curve
                        </button>
                      </>
                    )}
                  </div>
                )}
                {selected && "points" in selected && (
                  <div className="curve-actions">
                    <button
                      disabled={
                        !canEdit ||
                        !selection?.point ||
                        selected.points.findIndex(
                          (p) => p.id === selection.point,
                        ) <= 0 ||
                        selected.points.at(-1)?.id === selection?.point
                      }
                      onClick={() =>
                        void client.commands([
                          {
                            type: "SplitSpline",
                            target: "observation",
                            entity_id: selected.id,
                            point_id: selection!.point!,
                            new_entity_id: id("obs"),
                          },
                        ])
                      }
                    >
                      Split at knot
                    </button>
                    <select
                      aria-label="Merge curve"
                      disabled={!canEdit}
                      value=""
                      onChange={(e) =>
                        void client.commands([
                          {
                            type: "MergeSpline",
                            target: "observation",
                            entity_id: selected.id,
                            other_entity_id: e.target.value,
                          },
                        ])
                      }
                    >
                      <option value="">Merge with shared endpoint…</option>
                      {snapshot.observations
                        .filter(
                          (o) =>
                            o.id !== selected.id &&
                            "points" in o &&
                            o.points[0].id === selected.points.at(-1)?.id,
                        )
                        .map((o) => (
                          <option key={o.id} value={o.id}>
                            {o.id.slice(0, 16)}
                          </option>
                        ))}
                    </select>
                    <button
                      disabled={!canEdit}
                      onClick={() =>
                        void client
                          .commands([
                            {
                              type: "DeleteObservation",
                              observation_id: selected.id,
                            },
                          ])
                          .then((ok) => {
                            if (ok) choose(null);
                          })
                      }
                    >
                      Delete curve
                    </button>
                  </div>
                )}
                {reference ? (
                  <SourceCanvas
                    assist={cvOpen ? assist : undefined}
                    crop={cvOpen ? assist?.crop : undefined}
                    observations={snapshot.observations}
                    reference={reference}
                    url={
                      "/api/v1/projects/" +
                      snapshot.id +
                      "/references/" +
                      reference.id +
                      "/image"
                    }
                    preferences={prefs}
                    selection={selection}
                    tool={tool}
                    draft={draft}
                    writable={client.writable}
                    view={view}
                    onSelect={choose}
                    onClick={(p) => void add(p)}
                    onMove={move}
                    onCamera={(viewport) => preference({ viewport })}
                    onCancel={() => {
                      setDraft([]);
                      setTool("select");
                    }}
                  />
                ) : (
                  <div
                    className="import-empty"
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault();
                      if (e.dataTransfer.files[0])
                        void client.import(e.dataTransfer.files[0]);
                    }}
                  >
                    <div className="empty-glyph">▱</div>
                    <h2>Your source goes here</h2>
                    <p>
                      Drop a PNG or JPEG reference image. Original bytes stay
                      intact.
                    </p>
                    <ImportButton
                      disabled={!client.writable}
                      onFile={(file) => void client.import(file)}
                    />
                    <small>
                      Up to 64 MiB · 64 megapixels · No dimensions are inferred.
                    </small>
                  </div>
                )}
                <div className="readiness-panel">
                  <button
                    className="readiness-heading"
                    onClick={() => setShowReady(!showReady)}
                  >
                    <span>READINESS</span>
                    <small>
                      Source observations · {showReady ? "Hide" : "Show"} checks
                    </small>
                  </button>
                  {showReady && (
                    <div className="readiness-grid">
                      {[
                        "references",
                        "calibration",
                        "source_review",
                        "cage",
                        "cage_review",
                        "surfaces",
                      ].map((key) => {
                        const r = snapshot.readiness[key] as Ready | undefined;
                        return (
                          <details
                            key={key}
                            className={
                              r?.state === "READY" ? "ready" : "blocked"
                            }
                          >
                            <summary>
                              {key.replaceAll("_", " ")}
                              <b>{r?.state || "LEGACY"}</b>
                            </summary>
                            <p>
                              {r?.reasons?.join(" · ") || "Current core status"}
                            </p>
                          </details>
                        );
                      })}
                    </div>
                  )}
                </div>
              </main>
              <aside className="right-panel">
                {cvOpen && reference ? (
                  <Suspense fallback={<p>Opening annotation tools…</p>}>
                    <CVPanel
                      key={snapshot.id + reference.id + view}
                      snapshot={snapshot}
                      client={client}
                      reference={reference}
                      view={view}
                      initialTool={cvTool}
                      activation={cvActivation}
                      onCanvas={setAssist}
                      onExit={() => {
                        setCVOpen(false);
                        setAssist(undefined);
                        setTool("select");
                      }}
                    />
                  </Suspense>
                ) : (
                  <>
                    <div className="inspector-tabs">
                      <button
                        className={inspector === "properties" ? "active" : ""}
                        onClick={() => setInspector("properties")}
                      >
                        Properties
                      </button>
                      <button
                        className={inspector === "settings" ? "active" : ""}
                        onClick={() => setInspector("settings")}
                      >
                        Settings
                      </button>
                    </div>
                    {inspector === "settings" ? (
                      <Settings
                        snapshot={snapshot}
                        schemas={schemas}
                        profiles={profiles}
                        client={client}
                        disabled={!client.writable}
                      />
                    ) : selected ? (
                      <>
                        <Properties
                          key={selected.id}
                          observation={selected}
                          selection={selection}
                          client={client}
                          roles={snapshot.roles}
                          onRoleChanged={setRole}
                          canEdit={canEdit}
                        />
                        <label className="layer-assignment">
                          Display layer
                          <select
                            aria-label="Selected display layer"
                            value={layerFor(selected, prefs)}
                            onChange={(e) =>
                              preference({
                                assignments: {
                                  ...prefs.assignments,
                                  [selected.id]: e.target.value,
                                },
                              })
                            }
                          >
                            {Object.entries(prefs.layers || {})
                              .filter(([, l]) => l.category !== "image")
                              .map(([id, l]) => (
                                <option key={id} value={id}>
                                  {l.name}
                                </option>
                              ))}
                          </select>
                        </label>
                      </>
                    ) : (
                      <div className="inspector-empty">
                        <span>↖</span>
                        <h3>Select an observation</h3>
                        <p>
                          Inspect source coordinates, semantic role and
                          provenance here.
                        </p>
                        <small>
                          Only source observations are edited in this workspace.
                        </small>
                      </div>
                    )}
                  </>
                )}
              </aside>
            </div>
          )}
        </>
      )}
      <footer>
        <span>VehicleRecon Studio</span>
        <span>Local workspace · Original sources preserved</span>
        <span>Reference reconciliation / 0.4</span>
      </footer>
    </div>
  );
}
function ImportButton({
  disabled,
  onFile,
}: {
  disabled: boolean;
  onFile: (f: File) => void;
}) {
  return (
    <label className={"import-button " + (disabled ? "disabled" : "")}>
      Import reference
      <input
        type="file"
        aria-label="Import reference"
        accept="image/png,image/jpeg"
        disabled={disabled}
        onChange={(e) => {
          if (e.target.files?.[0]) onFile(e.target.files[0]);
          e.target.value = "";
        }}
      />
    </label>
  );
}
function NewProject({
  roots,
  profiles,
  api,
  onCreated,
}: {
  roots: { id: string; label: string; revision: string }[];
  profiles: string[];
  api: API;
  onCreated: (p: ProjectEntry) => Promise<void>;
}) {
  const [name, setName] = useState(""),
    [profile, setProfile] = useState("sedan"),
    [root, setRoot] = useState(""),
    [dimensions, setDimensions] = useState<Record<string, number | null>>({}),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function create() {
    setBusy(true);
    setError("");
    try {
      const chosen = roots.find((r) => r.id === root) || roots[0];
      const s = await api.post<Snapshot>("/projects", {
        name,
        profile,
        root_id: chosen.id,
        expected_revision: chosen.revision,
        dimensions,
      });
      await onCreated(s);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="new-project">
      <div className="section-caption">NEW VEHICLE STUDY</div>
      <h2>Create a draft</h2>
      <p>Begin with references. Add physical dimensions when you know them.</p>
      <SchemaField
        label="Project name"
        schema={{ type: "string" }}
        value={name}
        onChange={(v) => setName(String(v))}
      />
      <small>Letters, numbers, underscores or hyphens.</small>
      <SchemaField
        label="Profile"
        schema={{ enum: profiles }}
        value={profile}
        onChange={(v) => setProfile(String(v))}
      />
      <label>
        Workspace root
        <select
          aria-label="Workspace root"
          value={root || roots[0]?.id}
          onChange={(e) => setRoot(e.target.value)}
        >
          {roots.map((r) => (
            <option key={r.id} value={r.id}>
              {r.label}
            </option>
          ))}
        </select>
      </label>
      <details>
        <summary>Known dimensions (optional)</summary>
        {["length_m", "width_m", "height_m", "wheelbase_m"].map((key) => (
          <SchemaField
            key={key}
            label={"Initial " + key}
            schema={{ type: ["number", "null"], exclusiveMinimum: 0 }}
            value={dimensions[key]}
            onChange={(v) =>
              setDimensions((d) => ({ ...d, [key]: v as number | null }))
            }
          />
        ))}
      </details>
      <p className="new-project-note">
        v2 · DRAFT · Unknown dimensions stay unknown
      </p>
      {error && (
        <p role="alert" className="error-text">
          {error}
        </p>
      )}
      <button
        className="primary"
        disabled={!name || busy || !roots.length}
        onClick={() => void create()}
      >
        {busy ? "Creating…" : "Create project →"}
      </button>
    </section>
  );
}
