import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { SurfaceContext, SurfacePreview } from "./surface-types";
type Props = {
  context: SurfaceContext;
  preview: SurfacePreview | null;
  selected: string;
  picked: string;
  wire: boolean;
  normals: string;
  color: string;
  onPatch: (id: string) => void;
  onBoundary: (id: string) => void;
};
export function SurfacePreview3D(props: Props) {
  const host = useRef<HTMLDivElement>(null),
    latest = useRef(props),
    adapter = useRef<SurfaceScene | null>(null);
  latest.current = props;
  const [error, setError] = useState("");
  useEffect(() => {
    try {
      const scene = new SurfaceScene(host.current!, () => latest.current);
      adapter.current = scene;
      scene.update();
      return () => {
        scene.dispose();
        adapter.current = null;
      };
    } catch (e) {
      setError(String(e));
    }
  }, []);
  useEffect(() => {
    adapter.current?.update();
  }, [
    props.context,
    props.preview,
    props.selected,
    props.picked,
    props.wire,
    props.normals,
    props.color,
  ]);
  return (
    <section className="surface-canvas">
      <div
        ref={host}
        data-testid="surface-three-canvas"
        tabIndex={0}
        aria-label="Surface preview and boundary picking"
      />
      {error && <p role="alert">WebGL unavailable: {error}</p>}
      <small>
        Orbit: drag · Pan: right drag · Pick: click mesh or boundary · X
        longitudinal / Y lateral / Z up · metres
      </small>
      <button
        onClick={() => {
          if (adapter.current) {
            adapter.current.fitted = false;
            adapter.current.update();
          }
        }}
      >
        Fit preview
      </button>
    </section>
  );
}
class SurfaceScene {
  renderer = new THREE.WebGLRenderer({ antialias: true });
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(40, 1, 0.01, 1000);
  group = new THREE.Group();
  orbit: OrbitControls;
  observer: ResizeObserver;
  pickable: THREE.Object3D[] = [];
  start = new THREE.Vector2();
  fitted = false;
  surfaceFitted = false;
  constructor(
    public host: HTMLDivElement,
    public props: () => Props,
  ) {
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.setClearColor("#10202c");
    host.append(this.renderer.domElement);
    this.camera.up.set(0, 0, 1);
    this.camera.position.set(4, -5, 4);
    this.orbit = new OrbitControls(this.camera, this.renderer.domElement);
    this.orbit.addEventListener("change", this.draw);
    this.scene.add(
      this.group,
      new THREE.HemisphereLight(0xffffff, 0x667788, 3),
    );
    this.observer = new ResizeObserver(() => {
      this.camera.aspect = host.clientWidth / Math.max(host.clientHeight, 1);
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(host.clientWidth, host.clientHeight);
      this.draw();
    });
    this.observer.observe(host);
    host.addEventListener("pointerdown", this.down);
    host.addEventListener("pointerup", this.pick);
  }
  down = (e: PointerEvent) => {
    this.start.set(e.clientX, e.clientY);
  };
  pick = (e: PointerEvent) => {
    if (this.start.distanceTo(new THREE.Vector2(e.clientX, e.clientY)) > 5)
      return;
    const r = this.host.getBoundingClientRect(),
      ray = new THREE.Raycaster();
    ray.params.Line.threshold = 0.045;
    ray.setFromCamera(
      new THREE.Vector2(
        ((e.clientX - r.left) / r.width) * 2 - 1,
        (-(e.clientY - r.top) / r.height) * 2 + 1,
      ),
      this.camera,
    );
    const hits = ray.intersectObjects(this.pickable, false);
    const hit = hits.find((h) => h.object.userData.boundary) || hits[0];
    if (hit) {
      const d = hit.object.userData;
      d.patch
        ? this.props().onPatch(d.patch)
        : this.props().onBoundary(d.boundary);
    }
  };
  line(points: number[][], color: number, id?: string) {
    if (points.length < 2) return;
    const geometry = new THREE.BufferGeometry().setFromPoints(
      points.map((p) => new THREE.Vector3(...(p as [number, number, number]))),
    );
    const line = new THREE.Line(
      geometry,
      new THREE.LineBasicMaterial({ color, depthTest: false }),
    );
    line.renderOrder = 2;
    this.group.add(line);
    if (id) {
      line.userData.boundary = id;
      this.pickable.push(line);
      const a = points[0],
        b = points[Math.min(1, points.length - 1)],
        direction = new THREE.Vector3(...(b as [number, number, number])).sub(
          new THREE.Vector3(...(a as [number, number, number])),
        );
      if (direction.length() > 0)
        this.group.add(
          new THREE.ArrowHelper(
            direction.normalize(),
            new THREE.Vector3(...(a as [number, number, number])),
            0.15,
            color,
            0.04,
            0.025,
          ),
        );
    }
  }
  update() {
    const started = performance.now();
    this.clear();
    const p = this.props();
    for (const c of p.context.cage_boundaries)
      this.line(
        c.points,
        p.picked === c.id ? 0xffbb55 : 0x8ed9ff,
        "cage:" + c.id,
      );
    for (const boundary of p.preview?.boundaries || [])
      this.line(
        boundary.points,
        p.picked === boundary.id ? 0xffbb55 : 0x69bcbd,
        boundary.id,
      );
    for (const n of p.context.graph?.nodes || []) {
      if (p.preview?.boundaries?.some((b) => b.id === n.id)) continue;
      if (n.op === "polyline" && Array.isArray(n.parameters.points))
        this.line(
          n.parameters.points as number[][],
          p.picked === n.id ? 0xffbb55 : 0x69bcbd,
          n.id,
        );
    }
    for (const mesh of p.preview?.patches || []) {
      const g = new THREE.BufferGeometry();
      g.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(mesh.positions.flat(), 3),
      );
      g.setIndex(mesh.triangles.flat());
      g.setAttribute(
        "normal",
        new THREE.Float32BufferAttribute(mesh.normals.flat(), 3),
      );
      const n =
        p.color === "operation"
          ? mesh.operation
          : p.color === "semantic"
            ? mesh.id
            : mesh.status;
      let hash = 0;
      for (const c of n) hash = (hash * 31 + c.charCodeAt(0)) >>> 0;
      const bad = p.preview?.adjacency.some(
        (a) => (a.a === mesh.id || a.b === mesh.id) && a.status === "FAIL",
      );
      const color =
        p.color === "validation" || p.color === "continuity"
          ? mesh.status === "FAIL" || bad
            ? 0xe65b63
            : 0x68bd91
          : new THREE.Color().setHSL((hash % 360) / 360, 0.45, 0.48);
      const object = new THREE.Mesh(
        g,
        new THREE.MeshStandardMaterial({
          color,
          side: THREE.DoubleSide,
          emissive:
            mesh.id === p.selected || mesh.id === p.picked ? 0x335577 : 0,
          roughness: 0.7,
        }),
      );
      object.userData.patch = mesh.id;
      this.group.add(object);
      this.pickable.push(object);
      if (p.wire) {
        const wire = new THREE.LineSegments(
          new THREE.WireframeGeometry(g),
          new THREE.LineBasicMaterial({ color: 0x172631 }),
        );
        this.group.add(wire);
      }
      if (p.normals !== "off") {
        const rows =
          p.normals === "face"
            ? mesh.face_normals
            : mesh.positions.map((origin, i) => ({
                origin,
                normal: mesh.normals[i],
              }));
        const points = rows.flatMap((r) => [
          new THREE.Vector3(...(r.origin as [number, number, number])),
          new THREE.Vector3(
            ...(r.origin.map((v, i) => v + 0.05 * r.normal[i]) as [
              number,
              number,
              number,
            ]),
          ),
        ]);
        this.group.add(
          new THREE.LineSegments(
            new THREE.BufferGeometry().setFromPoints(points),
            new THREE.LineBasicMaterial({ color: 0xffdf68 }),
          ),
        );
      }
    }
    if (p.color === "continuity")
      for (const a of p.preview?.adjacency || [])
        this.line(
          a.samples || [],
          a.status === "FAIL"
            ? 0xff3344
            : a.status === "WARNING"
              ? 0xffbd55
              : 0x55ff99,
        );
    if (
      (!this.fitted || (!this.surfaceFitted && p.preview?.patches.length)) &&
      this.group.children.length
    ) {
      const box = new THREE.Box3().setFromObject(this.group),
        center = box.getCenter(new THREE.Vector3()),
        size = Math.max(box.getSize(new THREE.Vector3()).length(), 1);
      this.orbit.target.copy(center);
      this.camera.position
        .copy(center)
        .add(new THREE.Vector3(size, -size, size * 0.8));
      this.fitted = true;
      this.surfaceFitted = !!p.preview?.patches.length;
    }
    this.draw();
    this.host.dataset.meshCount = String(p.preview?.patches.length || 0);
    this.host.dataset.uploadMs = String(performance.now() - started);
    this.host.dataset.wireEdges = p.wire ? "actual-preview-mesh" : "off";
    this.host.dataset.pickTargets = JSON.stringify(
      this.pickable.map((object) => {
        const center = new THREE.Box3()
          .setFromObject(object)
          .getCenter(new THREE.Vector3())
          .project(this.camera);
        return {
          ...object.userData,
          x: ((center.x + 1) * this.host.clientWidth) / 2,
          y: ((1 - center.y) * this.host.clientHeight) / 2,
        };
      }),
    );
  }
  draw = () => {
    const start = performance.now();
    this.renderer.render(this.scene, this.camera);
    this.host.dataset.redrawMs = String(performance.now() - start);
  };
  clear() {
    this.group.traverse((o) => {
      const mesh = o as THREE.Mesh;
      mesh.geometry?.dispose();
      if (mesh.material)
        for (const m of Array.isArray(mesh.material)
          ? mesh.material
          : [mesh.material])
          m.dispose();
    });
    this.group.clear();
    this.pickable = [];
  }
  dispose() {
    this.clear();
    this.observer.disconnect();
    this.orbit.dispose();
    this.host.removeEventListener("pointerdown", this.down);
    this.host.removeEventListener("pointerup", this.pick);
    this.renderer.dispose();
    this.renderer.forceContextLoss();
    this.renderer.domElement.remove();
  }
}
