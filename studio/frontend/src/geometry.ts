import type { Camera, XY, Observation, Selection } from "./types";
export const sourceToScreen = (p: XY, v: Camera): XY => ({
  x: p.x * v.scale + v.x,
  y: p.y * v.scale + v.y,
});
export const screenToSource = (p: XY, v: Camera): XY => ({
  x: (p.x - v.x) / v.scale,
  y: (p.y - v.y) / v.scale,
});
export function zoomAt(v: Camera, p: XY, factor: number): Camera {
  const q = screenToSource(p, v),
    scale = Math.max(0.02, Math.min(32, v.scale * factor));
  return { scale, x: p.x - q.x * scale, y: p.y - q.y * scale };
}
export function fit(width: number, height: number, image: number[]): Camera {
  const scale = Math.min((width - 64) / image[0], (height - 64) / image[1]);
  return {
    scale,
    x: (width - image[0] * scale) / 2,
    y: (height - image[1] * scale) / 2,
  };
}
export function controls(o: Observation): { id?: string; pixel: number[] }[] {
  if ("points" in o) return o.points;
  if (o.kind === "point" && o.pixel) return [{ pixel: o.pixel }];
  if (o.kind === "circle") return [{ pixel: o.center }];
  return [];
}
type Hit = { pixel: number[]; selection: NonNullable<Selection> };
export class PickingIndex {
  cells = new Map<string, Hit[]>();
  size = 64;
  constructor(observations: Observation[]) {
    for (const o of observations)
      for (const p of controls(o)) {
        const key = this.key(p.pixel[0], p.pixel[1]);
        const items = this.cells.get(key) || [];
        items.push({
          pixel: p.pixel,
          selection: { entity: o.id, point: p.id },
        });
        this.cells.set(key, items);
      }
  }
  key(x: number, y: number) {
    return `${Math.floor(x / this.size)},${Math.floor(y / this.size)}`;
  }
  pick(p: XY, radius: number): Selection {
    let best: Hit | undefined,
      distance = radius;
    for (
      let x = Math.floor((p.x - radius) / this.size);
      x <= Math.floor((p.x + radius) / this.size);
      x++
    )
      for (
        let y = Math.floor((p.y - radius) / this.size);
        y <= Math.floor((p.y + radius) / this.size);
        y++
      )
        for (const item of this.cells.get(`${x},${y}`) || []) {
          const d = Math.hypot(item.pixel[0] - p.x, item.pixel[1] - p.y);
          if (d <= distance) {
            distance = d;
            best = item;
          }
        }
    return best?.selection ?? null;
  }
}
