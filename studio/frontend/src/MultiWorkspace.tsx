import { useEffect, useMemo, useRef, useState, lazy, Suspense } from "react";
import type { EditorClient } from "./api";
import { Properties } from "./Forms";
import { SourceCanvas } from "./Canvas";
const Preview3D = lazy(() =>
  import("./Preview3D").then((m) => ({ default: m.Preview3D })),
);
import {
  defaults,
  type AuthoringCommand,
  type Observation,
  type Preferences,
  type Selection,
  type Snapshot,
  type View,
} from "./types";
import {
  heatColors,
  type Analysis,
  type FitProposal,
  type ResidualRow,
  type WorldSelection,
} from "./multiview-types";

const views: View[] = ["side", "top", "front", "rear"];
const uuid = (prefix: string) =>
  prefix + "_" + crypto.randomUUID().replaceAll("-", "");
const ids = (text: string) => text.split(/[\s,]+/).filter(Boolean);
const severity = { FAIL: 0, UNKNOWN: 1, NEAR: 2, PASS: 3 };
type Props = {
  snapshot: Snapshot;
  client: EditorClient;
  preferences: Preferences;
  onPreference: (p: Partial<Preferences>) => void;
};
export function MultiWorkspace({
  snapshot,
  client,
  preferences: prefs,
  onPreference: preference,
}: Props) {
  const [analysis, setAnalysis] = useState<Analysis | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false);
  const [source, setSource] = useState<Selection>(null),
    [world, setWorld] = useState<WorldSelection>(null),
    [tab, setTab] = useState("Consistency");
  const [mode, setMode] = useState<"observation" | "world">("observation"),
    [constraint, setConstraint] = useState("X"),
    [pointTool, setPointTool] = useState(false),
    [role, setRole] = useState("roof");
  const [focus, setFocus] = useState<{
    key: number;
    pixels: Partial<Record<View, number[]>>;
  }>({ key: 0, pixels: {} });
  const [query, setQuery] = useState(""),
    [onlyFail, setOnlyFail] = useState(false),
    [filterView, setFilterView] = useState("all");
  const [name, setName] = useState(""),
    [xyz, setXyz] = useState(["0", "0", "0"]),
    [tolerance, setTolerance] = useState("2"),
    [critical, setCritical] = useState(true),
    [required, setRequired] = useState(true),
    [side, setSide] = useState("1");
  const [fitIds, setFitIds] = useState(""),
    [excluded, setExcluded] = useState(""),
    [fixedAxis, setFixedAxis] = useState(""),
    [fixedValue, setFixedValue] = useState("0"),
    [planeAxis, setPlaneAxis] = useState("Y"),
    [planeValue, setPlaneValue] = useState("0");
  const [proposal, setProposal] = useState<FitProposal | null>(null),
    [solving, setSolving] = useState(false);
  const [reviewKind, setReviewKind] = useState("source"),
    [decision, setDecision] = useState("NEEDS_CORRECTION"),
    [reviewer, setReviewer] = useState(""),
    [note, setNote] = useState("");
  const latest = useRef(snapshot);
  latest.current = snapshot;
  const latestPrefs = useRef(prefs);
  latestPrefs.current = prefs;
  const view = prefs.active_view || "side",
    layout = prefs.layout || "four";
  useEffect(() => {
    let alive = true;
    setLoading(true);
    setProposal(null);
    setError("");
    client.api
      .call<Analysis>(
        `/projects/${snapshot.id}/analysis?expected_revision=${snapshot.revision}`,
      )
      .then((data) => {
        if (alive && latest.current.revision === data.revision) {
          setAnalysis(data);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (alive) {
          setError(String(e.message || e));
          setLoading(false);
        }
      });
    return () => {
      alive = false;
    };
  }, [snapshot.id, snapshot.revision]);
  useEffect(() => {
    if (client.state.conflict) setProposal(null);
  }, [client.state.conflict]);
  const current = analysis?.revision === snapshot.revision && !loading;
  const rows = analysis?.residuals.rows || [];
  // V1 report markers are display-only DTOs, never writable authoring objects.
  const displayObservations = useMemo<Observation[]>(
    () =>
      snapshot.version === 2
        ? snapshot.observations
        : rows.map((r) => ({
            id: r.observation_id,
            kind: "point",
            view: r.view,
            semantic_role: r.semantic_role,
            pixel: r.observed_pixel,
            reference_id: "multiview",
            source_sha256: snapshot.references[0]?.sha256 || "",
            crop_id: "legacy-report",
            revision: 1,
            uncertainty_px: r.allowed_tolerance_px,
            visibility: "observed",
            measured: true,
            provenance: {
              type: "measured",
              method: "Verified historical independent source observation",
            },
          })),
    [snapshot.observations, analysis],
  );
  const selected = displayObservations.find((o) => o.id === source?.entity),
    selectedRow = rows.find(
      (r) =>
        r.observation_id === source?.entity &&
        (!source.point || r.observation_point_id === source.point),
    );
  useEffect(() => {
    if (world) {
      const p =
        world.kind === "landmark"
          ? analysis?.world_landmarks[world.entity]
          : analysis?.scene.controls.find(
              (c) => c.entity_id === world.entity && c.id === world.point,
            )?.xyz;
      setName(world.entity);
      if (p) setXyz(p.map(String));
      setFitIds(
        rows
          .filter((r) => r.world_entity_id === world.entity)
          .map((r) => r.observation_id)
          .filter((v, i, a) => a.indexOf(v) === i)
          .join(", "),
      );
    }
  }, [world?.entity, world?.point, world?.kind, analysis?.revision]);
  function focusRows(relevant: ResidualRow[]) {
    const pixels: Partial<Record<View, number[]>> = {};
    for (const r of relevant)
      if (r.observed_pixel && !pixels[r.view])
        pixels[r.view] = r.observed_pixel;
    setFocus((f) => ({ key: f.key + 1, pixels }));
  }
  function selectWorld(s: WorldSelection) {
    setWorld(s ? { ...s, focusKey: performance.now() } : null);
    setProposal(null);
    if (!s) return;
    const relevant = rows.filter(
      (r) =>
        r.world_entity_id === s.entity && (!s.point || r.point_id === s.point),
    );
    const first = relevant.find((r) => r.view === view) || relevant[0];
    if (first)
      setSource({
        entity: first.observation_id,
        point: first.observation_point_id,
      });
    focusRows(relevant);
  }
  function selectSource(s: Selection, v: View) {
    setSource(s);
    preference({ active_view: v });
    setProposal(null);
    const row = rows.find(
      (r) =>
        r.observation_id === s?.entity &&
        (!s?.point || r.observation_point_id === s.point),
    );
    if (row && prefs.sync_selection !== false) {
      setWorld({
        entity: row.world_entity_id,
        point: row.point_id,
        kind: row.binding_type === "curve_point" ? "control" : "landmark",
      });
      focusRows(rows.filter((r) => r.world_entity_id === row.world_entity_id));
    } else if (s && prefs.sync_semantic) {
      const o = displayObservations.find((o) => o.id === s.entity);
      focusRows(rows.filter((r) => r.semantic_role === o?.semantic_role));
    }
  }
  async function moveWorld(s: NonNullable<WorldSelection>, point: number[]) {
    if (mode !== "world") return false;
    return client.commands([
      s.kind === "landmark"
        ? { type: "MoveWorldLandmark", world_entity_id: s.entity, point }
        : {
            type: "MoveSplinePoint",
            target: "cage",
            entity_id: s.entity,
            point_id: s.point!,
            point,
          },
    ]);
  }
  async function applyXYZ() {
    const point = xyz.map(Number);
    if (!point.every(Number.isFinite) || !name) {
      setError("Enter a stable world ID and finite XYZ in metres.");
      return;
    }
    if (world && mode !== "world") {
      setError("Choose Move World Landmark before editing canonical XYZ.");
      return;
    }
    const ok = world
      ? await moveWorld(world, point)
      : await client.commands([
          { type: "AddWorldLandmark", world_entity_id: name, point },
        ]);
    if (ok && !world) setWorld({ entity: name, kind: "landmark" });
  }
  async function bind() {
    if (!selected || !world || world.kind === "curve") return;
    const id = uuid("link");
    const command: AuthoringCommand = {
      type: "BindObservation",
      correspondence: {
        id,
        observation_id: selected.id,
        observation_revision: selected.revision,
        world_entity_id: world.entity,
        binding_type: world.kind === "landmark" ? "landmark" : "curve_point",
        ...(world.point ? { point_id: world.point } : {}),
        ...(source?.point ? { observation_point_id: source.point } : {}),
        side: Number(side) as -1 | 0 | 1,
        required: required || critical,
        tolerance_policy: {
          metric: "euclidean_px",
          allowed_px: Number(tolerance),
        },
        semantic_role: selected.semantic_role,
        provenance: {
          type: selected.measured ? "measured" : "inferred",
          method: "Explicit user correspondence in Studio",
        },
      },
    };
    const commands: AuthoringCommand[] = [command];
    if (critical && analysis?.policy)
      commands.push({
        type: "SetCoveragePolicy",
        policy: {
          ...analysis.policy,
          critical_correspondence_ids: [
            ...analysis.policy.critical_correspondence_ids,
            id,
          ],
        },
      });
    await client.commands(commands);
  }
  async function unbind(row: ResidualRow) {
    const commands: AuthoringCommand[] = [];
    if (row.critical && analysis?.policy)
      commands.push({
        type: "SetCoveragePolicy",
        policy: {
          ...analysis.policy,
          critical_correspondence_ids:
            analysis.policy.critical_correspondence_ids.filter(
              (id) => id !== row.id,
            ),
        },
      });
    commands.push({ type: "UnbindObservation", correspondence_id: row.id });
    await client.commands(commands);
  }
  async function solve(plane = false) {
    setError("");
    setSolving(true);
    const before = snapshot.revision;
    try {
      if (!name) throw new Error("Choose or enter a world landmark ID.");
      const observation =
        selected &&
        ("pixel" in selected
          ? selected.pixel
          : "center" in selected
            ? selected.center
            : source?.point && "points" in selected
              ? selected.points.find((k) => k.id === source.point)?.pixel
              : null);
      const request = plane
        ? {
            world_entity_id: name,
            placement: {
              view: selected?.view || view,
              pixel: observation,
              normal: ["X", "Y", "Z"].map((a) => Number(a === planeAxis)),
              offset: Number(planeValue),
            },
          }
        : {
            world_entity_id: name,
            observation_ids: ids(fitIds),
            excluded_ids: ids(excluded),
            tolerance_px: Number(tolerance),
            constraints: fixedAxis
              ? [{ axis: fixedAxis, value: Number(fixedValue) }]
              : [],
          };
      const result = await client.api.post<FitProposal>(
        `/projects/${snapshot.id}/fit-proposals`,
        { expected_revision: before, lease_id: client.state.lease, request },
      );
      if (latest.current.revision !== before || client.state.conflict)
        throw new Error(
          "Evidence changed while solving; reload before applying a proposal.",
        );
      setProposal(result);
    } catch (e) {
      setError(String((e as Error).message));
    } finally {
      setSolving(false);
    }
  }
  async function addPoint(v: View, pixel: number[]) {
    if (!pointTool || mode !== "observation" || !client.writable) return;
    const reference =
      snapshot.references.find(
        (r) => r.role === snapshot.views[v]?.reference_role,
      ) ||
      snapshot.references.find(
        (r) => r.sha256 === analysis?.calibration_source_sha256,
      ) ||
      snapshot.references.find((r) => r.role === "multiview") ||
      snapshot.references[0];
    if (!reference) return;
    await client.commands([
      {
        type: "AddObservation",
        view: v,
        observation: {
          id: uuid("obs"),
          kind: "point",
          view: v,
          semantic_role: role,
          pixel,
          reference_id: reference.role,
          source_sha256: reference.sha256,
          crop_id: snapshot.views[v]?.crop_id[reference.role],
          revision: 1,
          uncertainty_px: 1,
          visibility: "observed",
          measured: true,
          provenance: {
            type: "measured",
            method: "Manual multi-view source annotation",
          },
        },
      },
    ]);
  }
  const filtered = useMemo(
    () =>
      rows
        .filter(
          (r) =>
            (!onlyFail || r.heat === "FAIL") &&
            (filterView === "all" || r.view === filterView) &&
            `${r.semantic_role} ${r.world_entity_id}`
              .toLowerCase()
              .includes(query.toLowerCase()),
        )
        .sort(
          (a, b) =>
            severity[a.heat] - severity[b.heat] ||
            Number(b.critical) - Number(a.critical) ||
            (b.residual_px || 0) - (a.residual_px || 0),
        ),
    [rows, onlyFail, filterView, query],
  );
  const secondary =
    prefs.secondary_view && prefs.secondary_view !== view
      ? prefs.secondary_view
      : views.find((v) => v !== view)!;
  const visibleViews =
    layout === "single" || layout === "split"
      ? [view]
      : layout === "two"
        ? [view, secondary]
        : views;
  const ref =
    snapshot.references.find(
      (r) => r.sha256 === analysis?.calibration_source_sha256,
    ) ||
    snapshot.references.find((r) => r.role === "multiview") ||
    snapshot.references[0];
  const canEdit = client.writable && current;
  return (
    <div
      className="multi-workspace"
      data-testid="multi-workspace"
      data-analysis-revision={analysis?.revision || ""}
      data-analysis-ready={current ? "true" : "false"}
    >
      <main className="multi-main">
        <div className="multi-toolbar">
          <label>
            Layout
            <select
              aria-label="Workspace layout"
              value={layout}
              onChange={(e) =>
                preference({ layout: e.target.value as Preferences["layout"] })
              }
            >
              <option value="single">Single view</option>
              <option value="two">2-up split</option>
              <option value="four">Four-view grid</option>
              <option value="split">2D + 3D split</option>
              <option value="all">Four views + 3D</option>
            </select>
          </label>
          <label>
            Active view
            <select
              aria-label="Active multi-view"
              value={view}
              onChange={(e) =>
                preference({ active_view: e.target.value as View })
              }
            >
              {views.map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          {layout === "two" && (
            <label>
              Second view
              <select
                aria-label="Second multi-view"
                value={secondary}
                onChange={(e) =>
                  preference({ secondary_view: e.target.value as View })
                }
              >
                {views
                  .filter((v) => v !== view)
                  .map((v) => (
                    <option key={v}>{v}</option>
                  ))}
              </select>
            </label>
          )}
          <div className="move-modes" role="group" aria-label="Move mode">
            <button
              className={mode === "observation" ? "active" : ""}
              onClick={() => {
                setMode("observation");
                setPointTool(false);
              }}
            >
              Move Observation
            </button>
            <button
              className={mode === "world" ? "active" : ""}
              onClick={() => {
                setMode("world");
                setPointTool(false);
              }}
            >
              Move World Landmark
            </button>
          </div>
          <label>
            Constraint
            <select
              aria-label="World drag constraint"
              value={constraint}
              onChange={(e) => setConstraint(e.target.value)}
            >
              {["X", "Y", "Z", "XY", "XZ", "YZ"].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <button
            disabled={!canEdit || mode !== "observation"}
            aria-pressed={pointTool}
            onClick={() => setPointTool(!pointTool)}
          >
            + Source point
          </button>
          {pointTool && (
            <select
              aria-label="Multi-view point role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              {snapshot.roles.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          )}
          <button
            aria-label="Multi-view Undo"
            disabled={!client.writable || !snapshot.history.undo}
            onClick={() => void client.run("undo")}
          >
            Undo
          </button>
          <button
            aria-label="Multi-view Redo"
            disabled={!client.writable || !snapshot.history.redo}
            onClick={() => void client.run("redo")}
          >
            Redo
          </button>
        </div>
        <div className={"mode-banner mode-" + mode} role="status">
          {mode === "observation"
            ? "SOURCE OBSERVATION · pixels only · world XYZ stays fixed"
            : "WORLD LANDMARK · canonical XYZ · all core projections refresh after commit"}
          {snapshot.read_only ? " · READ ONLY" : ""}
          {loading ? " · Refreshing evidence…" : ""}
        </div>
        <div className="multi-options">
          {[
            ["sync_selection", "Linked selection"],
            ["sync_semantic", "Semantic focus"],
            ["residual_vectors", "Residual vectors"],
            ["residual_labels", "Numeric labels"],
            ["heatmap", "Residual heatmap"],
          ].map(([key, label]) => (
            <label key={key}>
              <input
                type="checkbox"
                checked={
                  prefs[key as keyof Preferences] !== false &&
                  ((key !== "sync_semantic" && key !== "residual_labels") ||
                    !!prefs[key as keyof Preferences])
                }
                onChange={(e) => preference({ [key]: e.target.checked })}
              />
              {label}
            </label>
          ))}
          <span>
            ● observed · ⊕ projected · — residual · PASS / NEAR / FAIL / UNKNOWN
          </span>
        </div>
        {(error || analysis?.unavailable_reason) && (
          <p className="multi-error" role="alert">
            {error || analysis?.unavailable_reason}
          </p>
        )}
        <div className={"multi-viewports layout-" + layout}>
          {visibleViews.map((v) => {
            const framing = analysis?.views[v],
              linked = rows.find(
                (r) =>
                  r.world_entity_id === world?.entity &&
                  r.view === v &&
                  (!world?.point || r.point_id === world.point),
              );
            const selection =
              prefs.sync_selection !== false && linked
                ? {
                    entity: linked.observation_id,
                    point: linked.observation_point_id,
                  }
                : source;
            return (
              <div
                className={"multi-view " + (view === v ? "active-view" : "")}
                key={v}
                data-view={v}
              >
                <header>
                  <button
                    aria-label={"Focus " + v + " view"}
                    onClick={() => preference({ active_view: v })}
                  >
                    {v.toUpperCase()}
                  </button>
                  <span title={ref?.sha256}>
                    {ref?.role || "No reference"} {ref?.sha256.slice(0, 8)} ·
                    crop {framing?.crop?.join(", ") || "undefined"} ·{" "}
                    {framing?.calibrated ? "CALIBRATED" : "UNCALIBRATED"} ·{" "}
                    {framing?.rectification === "ACTIVE"
                      ? "RECTIFICATION ACTIVE / raw pixel canvas"
                      : "RAW SOURCE"}
                  </span>
                </header>
                {ref && analysis ? (
                  <SourceCanvas
                    observations={displayObservations}
                    reference={
                      snapshot.references.find(
                        (r) => r.role === snapshot.views[v]?.reference_role,
                      ) || ref
                    }
                    url={`/api/v1/projects/${snapshot.id}/references/${ref.id}/image`}
                    preferences={{
                      ...prefs,
                      layers: prefs.layers || defaults,
                      viewport: prefs.viewports?.[v],
                    }}
                    selection={selection}
                    tool={
                      pointTool && mode === "observation" ? "point" : "select"
                    }
                    draft={[]}
                    writable={canEdit && mode === "observation"}
                    view={v}
                    active={v === view}
                    crop={framing?.crop}
                    overlays={rows.filter((r) => r.view === v)}
                    focus={
                      focus.pixels[v]
                        ? { pixel: focus.pixels[v]!, key: focus.key }
                        : undefined
                    }
                    onActivate={() => preference({ active_view: v })}
                    onSelect={(s) => selectSource(s, v)}
                    onClick={(p) => void addPoint(v, p)}
                    onMove={(s, p) =>
                      client.commands([
                        s.point
                          ? {
                              type: "MoveSplinePoint",
                              target: "observation",
                              entity_id: s.entity,
                              point_id: s.point,
                              point: p,
                            }
                          : {
                              type: "MoveObservation",
                              observation_id: s.entity,
                              pixel: p,
                            },
                      ])
                    }
                    onCamera={(camera) => {
                      const viewports = {
                        ...latestPrefs.current.viewports,
                        [v]: camera,
                      };
                      latestPrefs.current = {
                        ...latestPrefs.current,
                        viewports,
                      };
                      preference({ viewports });
                    }}
                    onCancel={() => setPointTool(false)}
                  />
                ) : (
                  <p>Import a reference in the source editor first.</p>
                )}
              </div>
            );
          })}
          {(layout === "split" || layout === "all") && analysis && (
            <Suspense fallback={<p>Opening core-sampled 3D preview…</p>}>
              <Preview3D
                data={analysis.scene}
                rows={rows}
                selection={world}
                proposal={proposal}
                moveWorld={mode === "world"}
                constraint={constraint}
                writable={canEdit}
                onSelect={selectWorld}
                onMove={moveWorld}
              />
            </Suspense>
          )}
        </div>
        <div className="consistency-summary">
          {analysis?.groups.map((g) => (
            <span key={g.group} data-state={g.state}>
              {g.group}{" "}
              <b>
                {g.tolerance_status === "PASS"
                  ? "PASS" + (g.state === "WARNING" ? " · NEAR" : "")
                  : g.state}
              </b>
            </span>
          ))}
          <strong>
            Surfaces:{" "}
            {String(
              (snapshot.readiness.surfaces as { state?: string })?.state ||
                "LEGACY / BLOCKED",
            )}
          </strong>
        </div>
      </main>
      <aside className="multi-inspector">
        <nav>
          {[
            "Consistency",
            "Correspondence",
            "World",
            "Source",
            "Review",
            "Diagnostics",
          ].map((t) => (
            <button
              key={t}
              className={tab === t ? "active" : ""}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </nav>
        {tab === "Consistency" && (
          <div className="multi-details">
            <h2>Consistency</h2>
            <p>
              Every critical residual remains individual. Heat: residual /
              declared tolerance; near ≥ {analysis?.heat_policy.near_ratio}.
            </p>
            <label>
              Find semantic entity
              <input
                aria-label="Consistency search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
            <label>
              View filter
              <select
                value={filterView}
                onChange={(e) => setFilterView(e.target.value)}
              >
                <option value="all">All views</option>
                {views.map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={onlyFail}
                onChange={(e) => setOnlyFail(e.target.checked)}
              />
              Failures only
            </label>
            {analysis?.source_condition && (
              <strong className="source-condition">
                {analysis.source_condition} · historical read-only evidence
              </strong>
            )}
            <div className="consistency-rows">
              {filtered.map((r) => (
                <button
                  key={r.id}
                  className={"residual-row " + r.heat.toLowerCase()}
                  data-heat={r.heat}
                  data-entity={r.world_entity_id}
                  onClick={() =>
                    selectWorld({
                      entity: r.world_entity_id,
                      point: r.point_id,
                      kind:
                        r.binding_type === "curve_point"
                          ? "control"
                          : "landmark",
                    })
                  }
                >
                  <span>
                    {r.semantic_role}
                    <small>
                      {r.world_entity_id} · {r.view.toUpperCase()} ·{" "}
                      {[
                        r.critical && "CRITICAL",
                        r.required ? "REQUIRED" : "OPTIONAL",
                        r.inferred && "INFERRED",
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </small>
                  </span>
                  <strong>
                    {r.heat}
                    <small>
                      {r.residual_px?.toFixed(2) ?? "—"} /{" "}
                      {r.allowed_tolerance_px} px
                    </small>
                  </strong>
                </button>
              ))}
            </div>
            {!rows.length && (
              <p>
                No projected correspondences. Calibrate, create a world landmark
                and bind source evidence.
              </p>
            )}
            <h3>Coverage</h3>
            <table aria-label="Semantic view coverage">
              <thead>
                <tr>
                  <th>Entity</th>
                  {views.map((v) => (
                    <th key={v}>{v.toUpperCase()}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {analysis?.coverage.map((c) => (
                  <tr key={c.entity_id + ":" + (c.point_id || "")}>
                    <td>
                      <button
                        onClick={() =>
                          selectWorld({
                            entity: c.entity_id,
                            point: c.point_id || undefined,
                            kind: c.point_id ? "control" : "landmark",
                          })
                        }
                      >
                        {c.entity_id}
                        {c.point_id ? ":" + c.point_id : ""}
                      </button>
                    </td>
                    {views.map((v) => (
                      <td key={v}>{c.views[v] ? "✓" : "—"}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {tab === "Correspondence" && (
          <div className="multi-details">
            <h2>Explicit correspondence</h2>
            <p>
              SOURCE: {source?.entity || "Select an observation"}
              <br />
              WORLD: {world?.entity || "Choose a world entity"}
            </p>
            <label>
              World entity
              <select
                aria-label="Binding world entity"
                value={world?.entity || ""}
                onChange={(e) =>
                  setWorld(
                    e.target.value
                      ? { entity: e.target.value, kind: "landmark" }
                      : null,
                  )
                }
              >
                <option value="">Choose landmark</option>
                {Object.keys(analysis?.world_landmarks || {}).map((id) => (
                  <option key={id}>{id}</option>
                ))}
              </select>
            </label>
            <label>
              Tolerance (px)
              <input
                aria-label="Binding tolerance"
                type="number"
                min="0.01"
                value={tolerance}
                onChange={(e) => setTolerance(e.target.value)}
              />
            </label>
            <label>
              World instance
              <select
                aria-label="Binding instance"
                value={side}
                onChange={(e) => setSide(e.target.value)}
              >
                <option value="1">Canonical Y</option>
                <option value="-1">Mirrored Y</option>
                <option value="0">Centerline Y=0</option>
              </select>
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={critical}
                onChange={(e) => setCritical(e.target.checked)}
              />
              Critical
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={required}
                onChange={(e) => setRequired(e.target.checked)}
              />
              Required
            </label>
            <button
              disabled={
                !canEdit ||
                !selected ||
                !world ||
                world.kind === "curve" ||
                !!selectedRow
              }
              onClick={() => void bind()}
            >
              Bind observation to world
            </button>
            {selectedRow && (
              <>
                <p>
                  {selectedRow.critical
                    ? "CRITICAL"
                    : selectedRow.required
                      ? "REQUIRED"
                      : "OPTIONAL"}{" "}
                  · {selectedRow.id}
                </p>
                <button
                  disabled={!canEdit}
                  onClick={() => void unbind(selectedRow)}
                >
                  Unbind selected observation
                </button>
              </>
            )}
            <p>
              Critical policy:{" "}
              {analysis?.policy?.coverage_confirmed
                ? "CONFIRMED"
                : "UNCONFIRMED"}{" "}
              · {analysis?.policy?.critical_correspondence_ids.length || 0}{" "}
              explicitly designated links.
            </p>
            <button
              disabled={
                !canEdit ||
                !analysis?.policy?.critical_correspondence_ids.length
              }
              onClick={() =>
                void client.commands([
                  {
                    type: "SetCoveragePolicy",
                    policy: { ...analysis!.policy!, coverage_confirmed: true },
                  },
                ])
              }
            >
              Confirm authored critical coverage
            </button>
          </div>
        )}
        {tab === "World" && (
          <div className="multi-details">
            <h2>WORLD LANDMARK · metres</h2>
            <p>
              Canonical XYZ is separate from source pixels. Active mode:{" "}
              <strong>
                {mode === "world" ? "Move World Landmark" : "Move Observation"}
              </strong>
              .
            </p>
            <label>
              World selection
              <select
                aria-label="World landmark selection"
                value={world?.kind === "landmark" ? world.entity : ""}
                onChange={(e) =>
                  selectWorld(
                    e.target.value
                      ? { entity: e.target.value, kind: "landmark" }
                      : null,
                  )
                }
              >
                <option value="">Select landmark</option>
                {Object.keys(analysis?.world_landmarks || {}).map((id) => (
                  <option key={id}>{id}</option>
                ))}
              </select>
            </label>
            <button
              onClick={() => {
                setWorld(null);
                setName("");
                setXyz(["0", "0", "0"]);
                setFitIds(source?.entity || "");
                setProposal(null);
              }}
            >
              New world landmark
            </button>
            <label>
              Stable world ID
              <input
                aria-label="World ID"
                value={name}
                readOnly={!!world}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <div className="xyz-fields">
              {["X", "Y", "Z"].map((a, i) => (
                <label key={a}>
                  {a} (m)
                  <input
                    aria-label={"World " + a}
                    disabled={!canEdit}
                    type="number"
                    step="0.01"
                    value={xyz[i]}
                    onChange={(e) =>
                      setXyz((values) =>
                        values.map((v, j) => (i === j ? e.target.value : v)),
                      )
                    }
                  />
                </label>
              ))}
            </div>
            <button
              disabled={
                !canEdit ||
                !name ||
                (!!world && (mode !== "world" || world.kind === "curve"))
              }
              onClick={() => void applyXYZ()}
            >
              {world ? "Apply world XYZ" : "Create explicit XYZ"}
            </button>
            <details open>
              <summary>Solve proposal from observations</summary>
              <label>
                Observation IDs
                <textarea
                  aria-label="Fit observation IDs"
                  value={fitIds}
                  onChange={(e) => setFitIds(e.target.value)}
                />
              </label>
              <label>
                Explicitly excluded IDs
                <input
                  value={excluded}
                  onChange={(e) => setExcluded(e.target.value)}
                />
              </label>
              <label>
                Exact constraint
                <select
                  aria-label="Fit constraint axis"
                  value={fixedAxis}
                  onChange={(e) => setFixedAxis(e.target.value)}
                >
                  <option value="">No extra constraint</option>
                  {["X", "Y", "Z"].map((a) => (
                    <option key={a}>{a}</option>
                  ))}
                </select>
              </label>
              {fixedAxis && (
                <label>
                  Exact value (m)
                  <input
                    type="number"
                    value={fixedValue}
                    onChange={(e) => setFixedValue(e.target.value)}
                  />
                </label>
              )}
              <button
                disabled={
                  !canEdit ||
                  solving ||
                  world?.kind === "control" ||
                  world?.kind === "curve"
                }
                onClick={() => void solve()}
              >
                Solve from observations
              </button>
            </details>
            <details>
              <summary>Place on explicit plane</summary>
              <p>
                Select a calibrated source point. No invisible depth is
                inferred.
              </p>
              <label>
                Plane normal axis
                <select
                  aria-label="Placement plane"
                  value={planeAxis}
                  onChange={(e) => setPlaneAxis(e.target.value)}
                >
                  {["X", "Y", "Z"].map((a) => (
                    <option key={a}>{a}</option>
                  ))}
                </select>
              </label>
              <label>
                Plane coordinate (m)
                <input
                  type="number"
                  value={planeValue}
                  onChange={(e) => setPlaneValue(e.target.value)}
                />
              </label>
              <button
                disabled={!canEdit || !selected || !name}
                onClick={() => void solve(true)}
              >
                Preview plane placement
              </button>
            </details>
            {proposal && (
              <section className="fit-proposal" aria-label="Fit proposal">
                <h3>PROPOSAL · {proposal.status}</h3>
                <p>
                  Old XYZ:{" "}
                  {proposal.old_xyz?.map((v) => v.toFixed(5)).join(", ") ||
                    "new landmark"}
                </p>
                <p>
                  Proposed XYZ:{" "}
                  {proposal.proposed_xyz?.map((v) => v.toFixed(5)).join(", ") ||
                    "UNDERDETERMINED"}
                </p>
                <p>
                  RMS {proposal.rms_residual_px?.toFixed(3) ?? "—"} px · max{" "}
                  {proposal.max_residual_px?.toFixed(3) ?? "—"} px
                </p>
                <p>{proposal.ambiguity}</p>
                <pre>
                  {JSON.stringify(
                    {
                      conditioning: proposal.conditioning,
                      constraints: proposal.constraints,
                      used: proposal.observations_used,
                      excluded: proposal.observations_excluded,
                    },
                    null,
                    2,
                  )}
                </pre>
                {proposal.rows.map((r, i) => (
                  <p key={i}>
                    {r.view} · {r.status} · {r.residual_px?.toFixed(3)} /{" "}
                    {r.allowed_tolerance_px} px
                  </p>
                ))}
                <button
                  disabled={
                    !canEdit ||
                    !proposal.proposed_xyz ||
                    proposal.revision !== snapshot.revision
                  }
                  onClick={() =>
                    void client.run("apply-fit", {
                      proposal_id: proposal.proposal_id,
                    })
                  }
                >
                  APPLY proposal
                </button>
                <button onClick={() => setProposal(null)}>
                  CANCEL proposal
                </button>
              </section>
            )}
          </div>
        )}
        {tab === "Source" &&
          (selected && !snapshot.read_only ? (
            <Properties
              observation={selected}
              selection={source}
              client={client}
              roles={snapshot.roles}
              onRoleChanged={setRole}
              canEdit={canEdit && mode === "observation"}
            />
          ) : (
            <div className="multi-details">
              <h2>SOURCE OBSERVATION · pixels</h2>
              <p>
                Select a source observation. Legacy diagnostics are read-only.
              </p>
            </div>
          ))}
        {tab === "Review" && (
          <div className="multi-details">
            <h2>Explicit evidence review</h2>
            <label>
              Review type
              <select
                aria-label="Review type"
                value={reviewKind}
                onChange={(e) => {
                  setReviewKind(e.target.value);
                  setDecision("NEEDS_CORRECTION");
                }}
              >
                <option value="source">Source review</option>
                <option value="cage">Cage review</option>
              </select>
            </label>
            <p>
              Revision <code>{analysis?.revision}</code>
            </p>
            <p>
              Source:{" "}
              {analysis?.reviews.source?.status.decision ||
                analysis?.source_condition ||
                "MISSING"}{" "}
              {analysis?.reviews.source?.status.current
                ? "CURRENT"
                : "STALE / UNREVIEWED"}{" "}
              · Cage: {analysis?.reviews.cage?.status.decision || "MISSING"}{" "}
              {analysis?.reviews.cage?.status.current
                ? "CURRENT"
                : "STALE / UNREVIEWED"}
            </p>
            <p>
              Critical evidence:{" "}
              {rows.filter((r) => r.critical || r.required).length}; failures:{" "}
              {
                rows.filter(
                  (r) => (r.critical || r.required) && r.heat === "FAIL",
                ).length
              }
            </p>
            <p>
              Calibration:{" "}
              {views
                .map(
                  (v) =>
                    `${v}: ${analysis?.views[v]?.calibrated ? "calibrated" : "unavailable"}`,
                )
                .join(" · ")}
            </p>
            <details>
              <summary>Input identities, dimensions and provenance</summary>
              <pre>
                {JSON.stringify(
                  {
                    inputs: analysis?.input_identities,
                    dimensions: analysis?.dimensions,
                    measurements: analysis?.measurements,
                  },
                  null,
                  2,
                )}
              </pre>
            </details>
            <details>
              <summary>Coverage, proof identity and current decision</summary>
              <pre>
                {JSON.stringify(
                  {
                    coverage: analysis?.coverage,
                    policy: analysis?.policy,
                    review: analysis?.reviews[reviewKind],
                    rectification: analysis?.rectification_candidates,
                  },
                  null,
                  2,
                )}
              </pre>
            </details>
            <p>
              Inspected subject:{" "}
              <code>
                {analysis?.reviews[reviewKind]?.subject || "Unavailable"}
              </code>
            </p>
            <label>
              Decision
              <select
                aria-label="Review decision"
                value={decision}
                onChange={(e) => setDecision(e.target.value)}
              >
                {[
                  "NEEDS_CORRECTION",
                  "ACCEPTED",
                  ...(reviewKind === "source" ? ["INCONSISTENT_SOURCE"] : []),
                ].map((d) => (
                  <option key={d}>{d}</option>
                ))}
              </select>
            </label>
            <label>
              Reviewer
              <input
                aria-label="Reviewer"
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
              />
            </label>
            <label>
              Review note
              <textarea
                aria-label="Review note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </label>
            <button
              disabled={
                !canEdit ||
                !reviewer.trim() ||
                !note.trim() ||
                !analysis?.reviews[reviewKind]?.subject
              }
              onClick={() =>
                void client.run(reviewKind + "-review", {
                  decision,
                  reviewer,
                  note,
                  expected_subject: analysis!.reviews[reviewKind].subject,
                })
              }
            >
              Record {reviewKind} decision
            </button>
            <p>
              Source and cage acceptance are separate. Rejection/stale evidence
              blocks the core surface gate. No decision is automatic.
            </p>
          </div>
        )}
        {tab === "Diagnostics" && (
          <div className="multi-details">
            <h2>Axle / wheelbase</h2>
            <p>Front axle: {JSON.stringify(analysis?.wheelbase.front_axle)}</p>
            <p>Rear axle: {JSON.stringify(analysis?.wheelbase.rear_axle)}</p>
            <dl>
              {[
                ["World wheelbase", analysis?.wheelbase.world_wheelbase_m],
                [
                  "Authoritative wheelbase",
                  analysis?.wheelbase.authoritative_wheelbase_m,
                ],
                ["Difference", analysis?.wheelbase.difference_m],
              ].map(([label, value]) => (
                <div key={String(label)}>
                  <dt>{label}</dt>
                  <dd>
                    {typeof value === "number"
                      ? (value * 1000).toFixed(2) + " mm"
                      : "NOT ENOUGH DATA"}
                  </dd>
                </div>
              ))}
            </dl>
            <h3>SIDE / TOP longitudinal ratios</h3>
            <p>
              Normalized between shared front/rear axle datums. Diagnostic only;
              calibration is never altered.
            </p>
            <table aria-label="Longitudinal ratios">
              <thead>
                <tr>
                  <th>Semantic</th>
                  <th>SIDE</th>
                  <th>TOP</th>
                  <th>Δ / state</th>
                </tr>
              </thead>
              <tbody>
                {analysis?.legacy_ratios
                  ? analysis.legacy_ratios.landmarks.map((r) => (
                      <tr key={r.semantic}>
                        <td>{r.semantic}</td>
                        <td>{r.ratios.side?.toFixed(3)}</td>
                        <td>{r.ratios.top?.toFixed(3)}</td>
                        <td>
                          {r.difference_top_minus_side.toFixed(3)}{" "}
                          {r.compatibility}
                        </td>
                      </tr>
                    ))
                  : analysis?.ratios.rows.map((r) => (
                      <tr key={r.entity_id}>
                        <td>{r.semantic_role}</td>
                        <td>{r.views.side?.ratio.toFixed(3) ?? "—"}</td>
                        <td>{r.views.top?.ratio.toFixed(3) ?? "—"}</td>
                        <td>
                          {r.delta?.toFixed(3) ?? "—"} {r.status}
                        </td>
                      </tr>
                    ))}
              </tbody>
            </table>
            <h3>Rectification · display only</h3>
            <p>
              {views
                .map(
                  (v) =>
                    `${v.toUpperCase()}: ${analysis?.views[v]?.rectification || "NONE"}`,
                )
                .join(" · ")}
            </p>
            {!!analysis?.rectification_candidates.length &&
              analysis.rectification_candidates.map((c, i) => (
                <div key={i}>
                  <strong>
                    {String(c.status).includes("REJECTED")
                      ? "CANDIDATE REJECTED / NOT ACTIVE"
                      : `CANDIDATE ${String(c.status)} / NOT ACTIVE`}
                  </strong>
                  <p>
                    Max correction between axle datums:{" "}
                    {typeof c.max_correction_px === "number"
                      ? c.max_correction_px.toFixed(3) + " px"
                      : "unavailable"}{" "}
                    · Local scale min/max:{" "}
                    {Array.isArray(c.local_scale_range)
                      ? c.local_scale_range
                          .map((v) => Number(v).toFixed(6))
                          .join(" / ")
                      : "unavailable"}
                  </p>
                  <pre>{JSON.stringify(c, null, 2)}</pre>
                </div>
              ))}
            {analysis?.legacy_summary && (
              <details open>
                <summary>Verified historical residual summary</summary>
                <pre>{JSON.stringify(analysis.legacy_summary, null, 2)}</pre>
              </details>
            )}
            <p>{analysis?.scene.symmetry?.editing}</p>
          </div>
        )}
      </aside>
    </div>
  );
}
