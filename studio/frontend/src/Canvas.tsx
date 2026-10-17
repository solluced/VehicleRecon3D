import { useEffect, useRef, useState } from "react";
import Konva from "konva";
import { heatColors, type ResidualRow } from "./multiview-types";
import {
  controls,
  fit,
  PickingIndex,
  screenToSource,
  zoomAt,
} from "./geometry";
import {
  category,
  defaults,
  editable,
  layerFor,
  type AuthoringCommand,
  type Camera,
  type Observation,
  type Preferences,
  type Reference,
  type Selection,
  type XY,
} from "./types";
export type Tool =
  "select" | "pan" | "point" | "polyline" | "spline" | "insert";
type Props = {
  observations: Observation[];
  reference: Reference;
  url: string;
  preferences: Preferences;
  selection: Selection;
  tool: Tool;
  draft: number[][];
  writable: boolean;
  view: string;
  onSelect: (s: Selection) => void;
  onClick: (p: number[]) => void;
  onMove: (s: NonNullable<Selection>, p: number[]) => Promise<unknown>;
  onCamera: (v: Camera) => void;
  onCancel: () => void;
  overlays?: ResidualRow[];
  focus?: { pixel: number[]; key: number };
  crop?: number[];
  active?: boolean;
  onActivate?: () => void;
};
export function SourceCanvas(props: Props) {
  const host = useRef<HTMLDivElement>(null),
    adapter = useRef<Adapter | null>(null),
    latest = useRef(props);
  latest.current = props;
  const [zoom, setZoom] = useState(100),
    [cursor, setCursor] = useState(""),
    [loaded, setLoaded] = useState(false);
  useEffect(() => {
    const el = host.current!;
    const a = new Adapter(
      el,
      () => latest.current,
      (v) => {
        setZoom(v.scale * devicePixelRatio * 100);
        latest.current.onCamera(v);
      },
      setCursor,
    );
    adapter.current = a;
    const observer = new ResizeObserver(() => a.resize());
    observer.observe(el);
    return () => {
      observer.disconnect();
      a.destroy();
      adapter.current = null;
    };
  }, []);
  useEffect(() => {
    if (props.active !== false) host.current?.focus({ preventScroll: true });
  }, [props.tool]);
  useEffect(() => {
    setLoaded(false);
    adapter.current?.load(props.url, props.preferences.viewport, () =>
      setLoaded(true),
    );
  }, [props.url]);
  useEffect(() => {
    adapter.current?.update();
  }, [
    props.observations,
    props.selection,
    props.preferences.layers,
    props.preferences.assignments,
    props.draft,
    props.view,
    props.writable,
    props.overlays,
    props.preferences.residual_vectors,
    props.preferences.residual_labels,
    props.preferences.heatmap,
  ]);
  useEffect(() => {
    if (props.focus) adapter.current?.focus(props.focus.pixel);
  }, [props.focus?.key]);
  function nav(kind: string) {
    const a = adapter.current;
    if (!a) return;
    if (kind === "fit" || kind === "reset") a.fit();
    else if (kind === "one") a.one();
    else
      a.zoom(
        { x: a.stage.width() / 2, y: a.stage.height() / 2 },
        kind === "in" ? 1.25 : 0.8,
      );
  }
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (props.active === false) return;
      if ((e.target as HTMLElement).matches("input,textarea,select")) return;
      if (e.key === "f" || e.key === "F") nav("fit");
      if (e.key === "1") nav("one");
      if (e.key === "+") nav("in");
      if (e.key === "-") nav("out");
      const step: Record<string, number[]> = {
        ArrowLeft: [40, 0],
        ArrowRight: [-40, 0],
        ArrowUp: [0, 40],
        ArrowDown: [0, -40],
      };
      if (step[e.key]) {
        e.preventDefault();
        adapter.current?.pan(step[e.key][0], step[e.key][1]);
      }
      if (e.key === "Escape") {
        adapter.current?.cancel();
        props.onCancel();
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  });
  return (
    <section className="canvas-panel" aria-label="Reference editor">
      <div className="canvas-info">
        <span>
          {props.reference.role.toUpperCase()} <b>·</b>{" "}
          {props.reference.size.join(" × ")} px
        </span>
        <span>{cursor}</span>
      </div>
      <div
        ref={host}
        className={"canvas-host tool-" + props.tool}
        data-testid="canvas"
        role="application"
        tabIndex={0}
        aria-label="Source observation canvas"
      />
      <div className="canvas-nav">
        <span className="image-status">
          {loaded ? "SOURCE PIXELS" : "Loading image…"}
        </span>
        <button onClick={() => nav("out")} aria-label="Zoom out">
          −
        </button>
        <output data-testid="zoom">{zoom.toFixed(0)}%</output>
        <button onClick={() => nav("in")} aria-label="Zoom in">
          +
        </button>
        <button onClick={() => nav("fit")}>Fit</button>
        <button onClick={() => nav("one")}>1:1</button>
        <button onClick={() => nav("reset")}>Reset view</button>
      </div>
      <span className="canvas-hint">
        Scroll to zoom · Space / middle drag to pan · F fit · 1 actual pixels
      </span>
    </section>
  );
}

class Adapter {
  stage: Konva.Stage;
  imageLayer = new Konva.Layer({ listening: false });
  vectors = new Konva.Layer({ listening: false });
  imageGroup = new Konva.Group();
  vectorGroup = new Konva.Group();
  image: HTMLImageElement | null = null;
  camera: Camera = { x: 0, y: 0, scale: 1 };
  index = new PickingIndex([]);
  space = false;
  curvePaths: { id: string; path: Path2D; bounds: number[] }[] = [];
  gesture: {
    start: XY;
    camera: Camera;
    selection?: NonNullable<Selection>;
    original?: number[];
    pan: boolean;
    moved: boolean;
  } | null = null;
  override: { selection: NonNullable<Selection>; pixel: number[] } | null =
    null;
  frame = 0;
  destroyed = false;
  keyDown = (e: KeyboardEvent) => {
    if (
      e.code === "Space" &&
      !(e.target as HTMLElement).matches("input,textarea,select,button")
    ) {
      this.space = true;
      e.preventDefault();
    }
  };
  keyUp = (e: KeyboardEvent) => {
    if (e.code === "Space") this.space = false;
  };
  outside = () => {
    if (this.gesture) this.up();
  };
  constructor(
    public container: HTMLDivElement,
    public props: () => Props,
    public changed: (v: Camera) => void,
    public cursor: (v: string) => void,
  ) {
    this.stage = new Konva.Stage({
      container,
      width: container.clientWidth,
      height: container.clientHeight,
    });
    this.stage.add(this.imageLayer, this.vectors);
    this.imageLayer.add(this.imageGroup);
    this.vectors.add(this.vectorGroup);
    this.stage.on("wheel", (e) => {
      e.evt.preventDefault();
      this.zoom(
        this.stage.getPointerPosition()!,
        Math.exp(-e.evt.deltaY * 0.0015),
      );
    });
    this.stage.on("mousedown", (e) => this.down(e.evt));
    this.stage.on("mousemove", () => this.move());
    this.stage.on("mouseup", () => this.up());
    window.addEventListener("keydown", this.keyDown);
    window.addEventListener("keyup", this.keyUp);
    window.addEventListener("mouseup", this.outside);
    this.resize();
  }
  resize() {
    this.stage.size({
      width: this.container.clientWidth,
      height: this.container.clientHeight,
    });
    this.draw();
  }
  load(url: string, viewport: Camera | undefined, done: () => void) {
    const image = new Image();
    image.onload = () => {
      if (this.destroyed) return;
      this.image = image;
      this.imageGroup.destroyChildren();
      this.imageGroup.add(new Konva.Image({ image }));
      if (viewport && viewport.scale > 0) {
        this.camera = viewport;
        this.changed({ ...this.camera });
      } else this.fit();
      this.update();
      done();
    };
    image.src = url;
  }
  fit() {
    if (this.image) {
      const crop = this.props().crop;
      this.camera = fit(this.stage.width(), this.stage.height(), [
        crop ? crop[2] - crop[0] : this.image.naturalWidth,
        crop ? crop[3] - crop[1] : this.image.naturalHeight,
      ]);
      if (crop) {
        this.camera.x -= crop[0] * this.camera.scale;
        this.camera.y -= crop[1] * this.camera.scale;
      }
      this.changed({ ...this.camera });
      this.draw();
    }
  }
  one() {
    const center = { x: this.stage.width() / 2, y: this.stage.height() / 2 };
    this.zoom(center, 1 / (devicePixelRatio * this.camera.scale));
  }
  focus(pixel: number[]) {
    this.camera = {
      ...this.camera,
      x: this.stage.width() / 2 - pixel[0] * this.camera.scale,
      y: this.stage.height() / 2 - pixel[1] * this.camera.scale,
    };
    this.changed({ ...this.camera });
    this.draw();
  }
  zoom(pointer: XY, factor: number) {
    this.camera = zoomAt(this.camera, pointer, factor);
    this.changed({ ...this.camera });
    this.draw();
  }
  pan(x: number, y: number) {
    this.camera = {
      ...this.camera,
      x: this.camera.x + x,
      y: this.camera.y + y,
    };
    this.changed({ ...this.camera });
    this.draw();
  }
  source() {
    const p = screenToSource(
      this.stage.getPointerPosition() || { x: 0, y: 0 },
      this.camera,
    );
    return {
      x: Math.max(0, Math.min(this.image?.naturalWidth || 0, p.x)),
      y: Math.max(0, Math.min(this.image?.naturalHeight || 0, p.y)),
    };
  }
  down(e: MouseEvent) {
    if (!this.image || e.button === 2) return;
    this.container.focus({ preventScroll: true });
    this.props().onActivate?.();
    const p = this.props(),
      screen = this.stage.getPointerPosition()!,
      source = this.source();
    if (e.button === 1 || this.space || p.tool === "pan") {
      e.preventDefault();
      this.gesture = {
        start: screen,
        camera: { ...this.camera },
        pan: true,
        moved: false,
      };
      return;
    }
    if (p.tool !== "select") {
      if (p.writable) p.onClick([source.x, source.y]);
      return;
    }
    const began = performance.now();
    let hit = this.index.pick(source, 9 / this.camera.scale);
    if (!hit) {
      const c = this.vectors.getContext()._context,
        r = 9 / this.camera.scale;
      c.save();
      c.setTransform(1, 0, 0, 1, 0, 0);
      c.lineWidth = 2 * r;
      for (const curve of this.curvePaths) {
        const [l, t, right, b] = curve.bounds;
        if (
          source.x < l - r ||
          source.x > right + r ||
          source.y < t - r ||
          source.y > b + r
        )
          continue;
        if (c.isPointInStroke(curve.path, source.x, source.y)) {
          hit = { entity: curve.id };
          break;
        }
      }
      c.restore();
    }
    this.container.dataset.pickMs = String(performance.now() - began);
    p.onSelect(hit);
    if (hit) {
      const o = p.observations.find((o) => o.id === hit.entity)!;
      const point = controls(o).find((v) => v.id === hit.point);
      if (point && p.writable && editable(o, p.preferences))
        this.gesture = {
          start: screen,
          camera: { ...this.camera },
          selection: hit,
          original: [...point.pixel],
          pan: false,
          moved: false,
        };
    }
  }
  move() {
    const screen = this.stage.getPointerPosition();
    if (!screen) return;
    const q = this.source();
    this.cursor(`${q.x.toFixed(1)}, ${q.y.toFixed(1)} px`);
    const g = this.gesture;
    if (!g) return;
    g.moved =
      g.moved || Math.hypot(screen.x - g.start.x, screen.y - g.start.y) > 2;
    if (g.pan) {
      this.camera = {
        ...g.camera,
        x: g.camera.x + screen.x - g.start.x,
        y: g.camera.y + screen.y - g.start.y,
      };
      this.draw();
    } else if (g.selection && g.moved) {
      this.override = { selection: g.selection, pixel: [q.x, q.y] };
      this.draw();
    }
  }
  up() {
    const g = this.gesture;
    if (!g) return;
    this.gesture = null;
    if (g.pan) {
      this.changed({ ...this.camera });
      return;
    }
    if (g.moved && this.override && g.selection) {
      const point = [...this.override.pixel];
      void this.props()
        .onMove(g.selection, point)
        .finally(() => {
          this.override = null;
          this.draw();
        });
    } else {
      this.override = null;
      this.draw();
    }
  }
  cancel() {
    this.gesture = null;
    this.override = null;
    this.draw();
  }
  paintResiduals(context: Konva.Context) {
    const p = this.props(),
      c = context._context,
      s = this.camera.scale;
    this.container.dataset.residuals = String((p.overlays || []).length);
    if (!p.overlays) return;
    for (const row of p.overlays) {
      if (row.view !== p.view || !row.observed_pixel) continue;
      const [x, y] = row.observed_pixel,
        [px, py] = row.projected_pixel,
        color =
          p.preferences.heatmap === false ? "#b3c5d7" : heatColors[row.heat];
      c.strokeStyle = color;
      c.fillStyle = color;
      c.lineWidth = 1.5 / s;
      c.beginPath();
      c.arc(x, y, 4 / s, 0, Math.PI * 2);
      c.fill();
      if (p.preferences.residual_vectors !== false) {
        c.beginPath();
        c.moveTo(x, y);
        c.lineTo(px, py);
        c.stroke();
        c.beginPath();
        c.arc(px, py, 6 / s, 0, Math.PI * 2);
        c.moveTo(px - 8 / s, py);
        c.lineTo(px + 8 / s, py);
        c.moveTo(px, py - 8 / s);
        c.lineTo(px, py + 8 / s);
        c.stroke();
      }
      if (p.preferences.residual_labels) {
        c.font = `${11 / s}px Segoe UI`;
        c.fillText(
          `${row.heat} ${row.residual_px?.toFixed(1)} px`,
          px + 10 / s,
          py - 8 / s,
        );
      }
    }
  }
  visible() {
    const p = this.props();
    return p.observations.filter(
      (o) =>
        o.view === p.view &&
        o.reference_id === p.reference.role &&
        (
          p.preferences.layers?.[layerFor(o, p.preferences)] ??
          defaults[category(o)]
        ).visible,
    );
  }
  update() {
    this.index = new PickingIndex(this.visible());
    this.vectorGroup.destroyChildren();
    this.curvePaths = [];
    for (const o of this.visible())
      if ("points" in o) {
        const path = new Path2D(),
          bounds: number[][] = [];
        o.points.forEach((k, i) => {
          bounds.push(k.pixel);
          if (k.left) bounds.push(k.left);
          if (k.right) bounds.push(k.right);
          if (!i) path.moveTo(k.pixel[0], k.pixel[1]);
          else if (o.kind === "spline") {
            const a = o.points[i - 1].right ?? o.points[i - 1].pixel,
              b = k.left ?? k.pixel;
            path.bezierCurveTo(a[0], a[1], b[0], b[1], k.pixel[0], k.pixel[1]);
          } else path.lineTo(k.pixel[0], k.pixel[1]);
        });
        this.curvePaths.push({
          id: o.id,
          path,
          bounds: [
            Math.min(...bounds.map((p) => p[0])),
            Math.min(...bounds.map((p) => p[1])),
            Math.max(...bounds.map((p) => p[0])),
            Math.max(...bounds.map((p) => p[1])),
          ],
        });
      }
    const p = this.props(),
      layers = p.preferences.layers || defaults;
    for (const [id, layer] of Object.entries(layers))
      if (layer.category !== "image" && layer.visible) {
        const items = this.visible().filter(
          (o) => layerFor(o, p.preferences) === id,
        );
        if (items.length)
          this.vectorGroup.add(
            new Konva.Shape({
              opacity: layer.opacity,
              listening: false,
              sceneFunc: (context) => this.paint(context, items),
            }),
          );
      }
    this.vectorGroup.add(
      new Konva.Shape({
        listening: false,
        sceneFunc: (context) => {
          const c = context._context,
            draft = this.props().draft;
          if (!draft.length) return;
          c.beginPath();
          for (const [i, p] of draft.entries()) {
            if (i) c.lineTo(...(p as [number, number]));
            else c.moveTo(...(p as [number, number]));
          }
          c.strokeStyle = "#f5c56b";
          c.lineWidth = 2 / this.camera.scale;
          c.stroke();
          for (const p of draft) {
            c.beginPath();
            c.arc(p[0], p[1], 4 / this.camera.scale, 0, Math.PI * 2);
            c.fillStyle = "#f5c56b";
            c.fill();
          }
        },
      }),
    );
    this.vectorGroup.add(
      new Konva.Shape({
        listening: false,
        sceneFunc: (context) => this.paintResiduals(context),
      }),
    );
    this.draw();
  }
  paint(context: Konva.Context, items: Observation[]) {
    const c = context._context,
      s = this.camera.scale,
      selected = this.props().selection;
    for (const o of items) {
      const chosen = selected?.entity === o.id,
        color = chosen
          ? "#6de2cb"
          : o.visibility === "inferred"
            ? "#f29391"
            : "#7faefa";
      if (o.kind === "circle") {
        c.beginPath();
        c.arc(o.center[0], o.center[1], o.radius_px, 0, Math.PI * 2);
        c.strokeStyle = color;
        c.lineWidth = 1.5 / s;
        c.stroke();
      }
      const points = controls(o).map((k) => {
        const override = this.override;
        if (
          override?.selection.entity === o.id &&
          override.selection.point === k.id
        )
          return { ...k, pixel: override.pixel };
        return k;
      });
      if ("points" in o) {
        c.beginPath();
        points.forEach((k, i) => {
          if (!i) {
            c.moveTo(k.pixel[0], k.pixel[1]);
            return;
          }
          const prev = points[i - 1];
          const prevOriginal = o.points[i - 1],
            original = o.points[i];
          if (o.kind === "spline") {
            const handle = (
              point: typeof original,
              at: number[],
              side: "left" | "right",
            ) => {
              const value = point[side] ?? point.pixel;
              return [
                value[0] + at[0] - point.pixel[0],
                value[1] + at[1] - point.pixel[1],
              ];
            };
            const a = handle(prevOriginal, prev.pixel, "right"),
              b = handle(original, k.pixel, "left");
            c.bezierCurveTo(a[0], a[1], b[0], b[1], k.pixel[0], k.pixel[1]);
          } else c.lineTo(k.pixel[0], k.pixel[1]);
        });
        c.strokeStyle = color;
        c.lineWidth = (chosen ? 2.5 : 1.5) / s;
        c.setLineDash(o.visibility === "inferred" ? [6 / s, 4 / s] : []);
        c.stroke();
        c.setLineDash([]);
      }
    }
    // Batch handles by style; picking uses an independent spatial index.
    for (const chosen of [false, true]) {
      c.beginPath();
      for (const o of items) {
        if ((selected?.entity === o.id) !== chosen) continue;
        for (const k of controls(o)) {
          const ov = this.override;
          const pixel =
            ov?.selection.entity === o.id && ov.selection.point === k.id
              ? ov.pixel
              : k.pixel;
          c.moveTo(pixel[0] + 4 / s, pixel[1]);
          c.arc(pixel[0], pixel[1], (chosen ? 5 : 3.5) / s, 0, Math.PI * 2);
        }
      }
      c.fillStyle = chosen ? "#6de2cb" : "#a9c8fc";
      c.fill();
    }
  }
  draw() {
    if (this.frame) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      const began = performance.now();
      for (const group of [this.imageGroup, this.vectorGroup]) {
        group.position({ x: this.camera.x, y: this.camera.y });
        group.scale({ x: this.camera.scale, y: this.camera.scale });
      }
      const layer = this.props().preferences.layers?.image ?? defaults.image;
      this.imageGroup.visible(layer.visible);
      this.imageGroup.opacity(layer.opacity);
      this.stage.draw();
      this.container.dataset.viewport = JSON.stringify(this.camera);
      this.container.dataset.drawMs = String(performance.now() - began);
    });
  }
  destroy() {
    this.destroyed = true;
    cancelAnimationFrame(this.frame);
    window.removeEventListener("keydown", this.keyDown);
    window.removeEventListener("keyup", this.keyUp);
    window.removeEventListener("mouseup", this.outside);
    this.stage.destroy();
  }
}
