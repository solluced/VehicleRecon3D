import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import {
  heatColors,
  type SceneData,
  type WorldSelection,
  type FitProposal,
  type ResidualRow,
} from "./multiview-types";
import { constrainWorldMove } from "./world-tools";

type Props = {
  data: SceneData;
  selection: WorldSelection;
  rows: ResidualRow[];
  proposal: FitProposal | null;
  moveWorld: boolean;
  constraint: string;
  writable: boolean;
  onSelect: (s: WorldSelection) => void;
  onMove: (s: NonNullable<WorldSelection>, xyz: number[]) => Promise<unknown>;
};
export function Preview3D(props: Props) {
  const host = useRef<HTMLDivElement>(null),
    adapter = useRef<Preview | null>(null),
    latest = useRef(props);
  latest.current = props;
  const [error, setError] = useState("");
  useEffect(() => {
    try {
      const a = new Preview(host.current!, () => latest.current);
      adapter.current = a;
      return () => {
        a.dispose();
        adapter.current = null;
      };
    } catch (e) {
      setError("WebGL preview unavailable: " + String(e));
    }
  }, []);
  useEffect(() => {
    adapter.current?.update();
  }, [
    props.data,
    props.selection,
    props.rows,
    props.proposal,
    props.moveWorld,
    props.constraint,
    props.writable,
  ]);
  return (
    <section className="preview3d" aria-label="Live 3D cage">
      <header>
        <strong>WORLD · metres</strong>
        <span>X longitudinal · Y lateral · Z up</span>
      </header>
      <div
        className="three-host"
        ref={host}
        data-testid="three-canvas"
        aria-label="3D cage canvas"
        tabIndex={0}
      />
      {error && <p role="alert">{error}</p>}
      <nav className="three-nav">
        {["Fit all", "FRONT", "REAR", "LEFT", "RIGHT", "TOP", "3/4"].map(
          (name) => (
            <button key={name} onClick={() => adapter.current?.preset(name)}>
              {name}
            </button>
          ),
        )}
      </nav>
      <footer>
        Core samples ·{" "}
        {props.data.curves.some((c) => c.approximate)
          ? "AUTO: approximate control polygons"
          : "piecewise linear preview"}{" "}
        · Orbit: drag · Pan: right drag · Zoom: wheel
        {props.data.symmetry?.declared ? " · Symmetry Y=0: display only" : ""}
      </footer>
    </section>
  );
}

class Preview {
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(38, 1, 0.01, 1000);
  orbit: OrbitControls;
  gizmo: TransformControls;
  content = new THREE.Group();
  pickable: THREE.Object3D[] = [];
  selected: THREE.Object3D | null = null;
  observer: ResizeObserver;
  frame = 0;
  disposed = false;
  center = new THREE.Vector3(0, 0, 0.6);
  extent = 5;
  start = new THREE.Vector2();
  dragStart: number[] | null = null;
  didDrag = false;
  lastFocus = "";
  constructor(
    public host: HTMLDivElement,
    public props: () => Props,
  ) {
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.setClearColor("#111b25");
    host.appendChild(this.renderer.domElement);
    this.camera.up.set(0, 0, 1);
    this.camera.position.set(-6, -7, 4);
    this.scene.add(this.content);
    const grid = new THREE.GridHelper(20, 40, 0x536a75, 0x293a48);
    grid.rotation.x = Math.PI / 2;
    this.scene.add(grid, new THREE.AxesHelper(2));
    this.orbit = new OrbitControls(this.camera, this.renderer.domElement);
    this.orbit.target.copy(this.center);
    this.orbit.enableDamping = false;
    this.orbit.addEventListener("change", () => this.draw());
    this.gizmo = new TransformControls(this.camera, this.renderer.domElement);
    this.gizmo.setMode("translate");
    this.gizmo.setSpace("world");
    this.gizmo.size = 0.8;
    this.scene.add(this.gizmo.getHelper());
    this.gizmo.addEventListener("dragging-changed", (e) => {
      this.orbit.enabled = !e.value;
    });
    this.gizmo.addEventListener("mouseDown", () => {
      this.dragStart = this.selected?.position.toArray() || null;
      this.didDrag = false;
    });
    this.gizmo.addEventListener("objectChange", () => {
      this.didDrag = true;
      host.dataset.dragPreview = JSON.stringify(
        this.selected?.position.toArray(),
      );
      this.draw();
    });
    this.gizmo.addEventListener("mouseUp", () => {
      const p = this.props(),
        before = this.dragStart,
        object = this.selected;
      this.dragStart = null;
      if (!before || !object || !p.selection || !p.writable || !p.moveWorld)
        return;
      const xyz = constrainWorldMove(
        before,
        object.position.toArray(),
        p.constraint,
      );
      if (xyz.some((v, i) => Math.abs(v - before[i]) > 1e-10))
        void p.onMove(p.selection, xyz).finally(() => this.update());
    });
    this.gizmo.addEventListener("change", () => this.draw());
    this.renderer.domElement.addEventListener("pointerdown", this.down);
    this.renderer.domElement.addEventListener("pointerup", this.up);
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(host);
    this.resize();
    this.update();
    this.preset("3/4");
  }
  down = (e: PointerEvent) => {
    this.start.set(e.clientX, e.clientY);
    this.didDrag = false;
  };
  up = (e: PointerEvent) => {
    if (
      this.didDrag ||
      this.gizmo.dragging ||
      this.start.distanceTo(new THREE.Vector2(e.clientX, e.clientY)) > 4
    )
      return;
    const box = this.renderer.domElement.getBoundingClientRect(),
      ray = new THREE.Raycaster();
    ray.params.Line = { threshold: this.extent * 0.008 };
    ray.setFromCamera(
      new THREE.Vector2(
        ((e.clientX - box.left) / box.width) * 2 - 1,
        (-(e.clientY - box.top) / box.height) * 2 + 1,
      ),
      this.camera,
    );
    const hits = ray.intersectObjects(this.pickable, false);
    const hit = (
      hits.find((h) => h.object instanceof THREE.Mesh) ||
      hits.find((h) => h.object.userData.selection)
    )?.object;
    if (hit) this.props().onSelect(hit.userData.selection as WorldSelection);
  };
  resize() {
    const w = this.host.clientWidth,
      h = this.host.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.draw();
  }
  clear() {
    this.gizmo.detach();
    const geometries = new Set<THREE.BufferGeometry>(),
      materials = new Set<THREE.Material>();
    this.content.traverse((o) => {
      if (o instanceof THREE.Mesh || o instanceof THREE.Line) {
        geometries.add(o.geometry);
        for (const m of Array.isArray(o.material) ? o.material : [o.material])
          materials.add(m);
      }
    });
    this.content.clear();
    geometries.forEach((g) => g.dispose());
    materials.forEach((m) => m.dispose());
    this.pickable = [];
    this.selected = null;
  }
  update() {
    if (this.disposed || this.gizmo.dragging) return;
    this.clear();
    const p = this.props(),
      data = p.data;
    const all = [
      ...Object.values(data.landmarks),
      ...data.controls.map((c) => c.xyz),
      ...data.curves.flatMap((c) => c.world_samples),
      ...(data.wheels || []).flatMap((w) => w.world_samples),
    ];
    if (all.length) {
      const box = new THREE.Box3().setFromPoints(
        all.map((v) => new THREE.Vector3().fromArray(v)),
      );
      box.getCenter(this.center);
      this.extent = Math.max(2, box.getSize(new THREE.Vector3()).length());
    }
    const sphere = new THREE.SphereGeometry(this.extent * 0.009, 12, 8);
    const addPoint = (
      xyz: number[],
      s: NonNullable<WorldSelection>,
      big = false,
    ) => {
      const chosen =
        p.selection?.entity === s.entity &&
        p.selection.kind === s.kind &&
        p.selection.point === s.point;
      const rows = p.rows.filter((r) => r.world_entity_id === s.entity),
        status = rows.some((r) => r.heat === "FAIL")
          ? "FAIL"
          : rows.some((r) => r.heat === "NEAR")
            ? "NEAR"
            : rows.length
              ? "PASS"
              : "UNKNOWN";
      const mesh = new THREE.Mesh(
        sphere,
        new THREE.MeshBasicMaterial({
          color: chosen ? "#ffffff" : heatColors[status],
        }),
      );
      mesh.position.fromArray(xyz);
      mesh.scale.setScalar(chosen ? 1.55 : big ? 1.2 : 0.7);
      mesh.userData.selection = s;
      this.content.add(mesh);
      this.pickable.push(mesh);
      if (chosen) this.selected = mesh;
    };
    for (const [id, xyz] of Object.entries(data.landmarks))
      addPoint(xyz, { entity: id, kind: "landmark" }, true);
    for (const c of data.controls)
      if (!c.landmark)
        addPoint(c.xyz, { entity: c.entity_id, point: c.id, kind: "control" });
    for (const counterpart of data.mirrored_controls || []) {
      const mesh = new THREE.Mesh(
        sphere,
        new THREE.MeshBasicMaterial({
          color: "#7891aa",
          wireframe: true,
          transparent: true,
          opacity: 0.65,
        }),
      );
      mesh.position.fromArray(counterpart.xyz);
      mesh.scale.setScalar(0.75);
      this.content.add(mesh);
    }
    const addLine = (
      points: number[][],
      color: string,
      selection: WorldSelection,
      dashed = false,
    ) => {
      const geometry = new THREE.BufferGeometry().setFromPoints(
        points.map((v) => new THREE.Vector3().fromArray(v)),
      );
      const material = dashed
        ? new THREE.LineDashedMaterial({
            color,
            dashSize: this.extent * 0.02,
            gapSize: this.extent * 0.012,
          })
        : new THREE.LineBasicMaterial({ color });
      const line = new THREE.Line(geometry, material);
      if (dashed) line.computeLineDistances();
      if (selection) {
        line.userData.selection = selection;
        this.pickable.push(line);
      }
      this.content.add(line);
    };
    for (const c of data.curves) {
      const entity = c.source_entity_id || c.entity_id;
      addLine(
        c.cyclic ? [...c.world_samples, c.world_samples[0]] : c.world_samples,
        p.selection?.entity === entity
          ? "#ffffff"
          : c.kind === "section"
            ? "#e6b978"
            : "#72a5e5",
        { entity, kind: "curve" },
        c.approximate,
      );
    }
    for (const w of data.wheels || [])
      addLine(w.world_samples, "#4c807b", null);
    if (data.symmetry?.declared) {
      const plane = new THREE.Mesh(
        new THREE.PlaneGeometry(this.extent, this.extent),
        new THREE.MeshBasicMaterial({
          color: "#7294af",
          transparent: true,
          opacity: 0.06,
          side: THREE.DoubleSide,
          depthWrite: false,
        }),
      );
      plane.rotation.x = Math.PI / 2;
      plane.position.set(this.center.x, 0, this.center.z);
      this.content.add(plane);
    }
    if (p.proposal?.proposed_xyz) {
      const ghost = new THREE.Mesh(
        new THREE.SphereGeometry(this.extent * 0.02, 12, 8),
        new THREE.MeshBasicMaterial({
          color: "#f2c572",
          wireframe: true,
          transparent: true,
          opacity: 0.7,
        }),
      );
      ghost.position.fromArray(p.proposal.proposed_xyz);
      this.content.add(ghost);
      if (p.proposal.old_xyz)
        addLine(
          [p.proposal.old_xyz, p.proposal.proposed_xyz],
          "#f2c572",
          null,
          true,
        );
    }
    if (
      this.selected &&
      p.moveWorld &&
      p.writable &&
      p.selection?.kind !== "curve"
    ) {
      for (const axis of ["X", "Y", "Z"] as const)
        this.gizmo[("show" + axis) as "showX"] = p.constraint.includes(axis);
      this.gizmo.showE = false;
      this.gizmo.showXYZE = false;
      this.gizmo.showXY = p.constraint === "XY";
      this.gizmo.showXZ = p.constraint === "XZ";
      this.gizmo.showYZ = p.constraint === "YZ";
      this.gizmo.attach(this.selected);
    }
    const focusKey = p.selection
      ? `${p.selection.entity}:${p.selection.point || ""}:${p.selection.focusKey || ""}`
      : "";
    if (focusKey && focusKey !== this.lastFocus) {
      let target = this.selected?.position.clone();
      if (!target && p.selection?.kind === "curve") {
        const curve = data.curves.find(
          (c) => (c.source_entity_id || c.entity_id) === p.selection?.entity,
        );
        if (curve)
          target = new THREE.Box3()
            .setFromPoints(
              curve.world_samples.map((v) => new THREE.Vector3().fromArray(v)),
            )
            .getCenter(new THREE.Vector3());
      }
      if (target) {
        this.camera.position.add(target.clone().sub(this.orbit.target));
        this.orbit.target.copy(target);
        this.orbit.update();
      }
    }
    this.lastFocus = focusKey;
    this.host.dataset.selected = p.selection?.entity || "";
    this.host.dataset.landmarks = String(Object.keys(data.landmarks).length);
    this.host.dataset.proposal = p.proposal?.proposal_id || "";
    this.draw();
  }
  preset(name: string) {
    const dirs: Record<string, number[]> = {
      FRONT: [-1, 0, 0],
      REAR: [1, 0, 0],
      LEFT: [0, -1, 0],
      RIGHT: [0, 1, 0],
      TOP: [0, 0, 1],
      "3/4": [-1, -1, 0.7],
    };
    this.camera.up.set(0, 0, 1);
    if (name === "TOP") this.camera.up.set(0, 1, 0);
    const d = new THREE.Vector3()
      .fromArray(dirs[name] || [-1, -1, 0.7])
      .normalize();
    this.camera.position
      .copy(this.center)
      .addScaledVector(d, this.extent * 1.65);
    this.orbit.target.copy(this.center);
    this.orbit.update();
    this.draw();
  }
  draw() {
    if (this.frame || this.disposed) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      if (this.disposed) return;
      const start = performance.now();
      this.renderer.render(this.scene, this.camera);
      const points: Record<string, number[]> = {};
      for (const object of this.pickable)
        if (object instanceof THREE.Mesh) {
          const s = object.userData.selection as NonNullable<WorldSelection>,
            v = object.position.clone().project(this.camera);
          points[s.entity + (s.point ? ":" + s.point : "")] = [
            ((v.x + 1) * this.host.clientWidth) / 2,
            ((-v.y + 1) * this.host.clientHeight) / 2,
          ];
        }
      const handles: Record<string, number[][]> = {};
      this.gizmo.getHelper().traverse((o) => {
        if (
          !(o instanceof THREE.Mesh) ||
          !["X", "Y", "Z", "XY", "XZ", "YZ"].includes(o.name)
        )
          return;
        let visible = true;
        for (let part: THREE.Object3D | null = o; part; part = part.parent)
          if (!part.visible) visible = false;
        const material = Array.isArray(o.material) ? o.material[0] : o.material;
        if (!visible || material.opacity < 0.1) return;
        o.geometry.computeBoundingSphere();
        const v = o.geometry
          .boundingSphere!.center.clone()
          .applyMatrix4(o.matrixWorld)
          .project(this.camera);
        (handles[o.name] ??= []).push([
          ((v.x + 1) * this.host.clientWidth) / 2,
          ((-v.y + 1) * this.host.clientHeight) / 2,
        ]);
      });
      this.host.dataset.handles = JSON.stringify(handles);
      this.host.dataset.points = JSON.stringify(points);
      this.host.dataset.drawMs = String(performance.now() - start);
      this.host.dataset.camera = JSON.stringify(this.camera.position.toArray());
    });
  }
  dispose() {
    this.disposed = true;
    cancelAnimationFrame(this.frame);
    this.observer.disconnect();
    this.renderer.domElement.removeEventListener("pointerdown", this.down);
    this.renderer.domElement.removeEventListener("pointerup", this.up);
    this.clear();
    this.orbit.dispose();
    this.gizmo.dispose();
    this.scene.traverse((o) => {
      if (o instanceof THREE.Mesh || o instanceof THREE.Line) {
        o.geometry.dispose();
        for (const m of Array.isArray(o.material) ? o.material : [o.material])
          m.dispose();
      }
    });
    this.renderer.dispose();
    this.renderer.forceContextLoss();
    this.renderer.domElement.remove();
  }
}
