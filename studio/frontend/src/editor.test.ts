import { describe, it, expect, vi } from "vitest";
import {
  fit,
  zoomAt,
  sourceToScreen,
  screenToSource,
  PickingIndex,
} from "./geometry";
import { editable, defaults, type Observation, type Snapshot } from "./types";
import { EditorClient, APIError } from "./api";
import type { API } from "./api";
const point = {
  id: "one",
  kind: "point",
  view: "side",
  pixel: [100, 200],
  semantic_role: "roof",
} as Observation;
describe("source coordinates and navigation", () => {
  it.each([0.05, 1, 5])("roundtrips pixels at scale %s", (scale) => {
    const camera = { x: 40, y: -80, scale };
    const p = { x: 250, y: 300 };
    expect(screenToSource(sourceToScreen(p, camera), camera)).toEqual(p);
  });
  it("keeps the source pixel under pointer fixed while zooming", () => {
    const v = { x: 20, y: 30, scale: 0.2 },
      p = { x: 300, y: 200 };
    const next = zoomAt(v, p, 1.7);
    const a = screenToSource(p, v),
      b = screenToSource(p, next);
    expect(a.x).toBeCloseTo(b.x, 10);
    expect(a.y).toBeCloseTo(b.y, 10);
  });
  it("fits a 4K source without changing aspect ratio", () => {
    const v = fit(1000, 600, [3840, 2160]);
    expect(v.scale * 3840).toBeLessThanOrEqual(936);
    expect(v.x).toBeGreaterThan(0);
  });
  it("clamps zoom to supported bounds", () => {
    expect(zoomAt({ x: 0, y: 0, scale: 32 }, { x: 0, y: 0 }, 5).scale).toBe(32);
  });
});
describe("picking and layer edit policy", () => {
  it("picks by pixel distance and stable identity", () => {
    const index = new PickingIndex([point]);
    expect(index.pick({ x: 103, y: 200 }, 5)?.entity).toBe("one");
    expect(index.pick({ x: 500, y: 200 }, 5)).toBeNull();
  });
  it("honors locked and hidden presentation layers", () => {
    expect(editable(point, { layers: defaults })).toBe(true);
    expect(
      editable(point, {
        layers: {
          ...defaults,
          observations: { ...defaults.observations, locked: true },
        },
      }),
    ).toBe(false);
    expect(
      editable(point, {
        layers: {
          ...defaults,
          observations: { ...defaults.observations, visible: false },
        },
      }),
    ).toBe(false);
  });
});
function session() {
  const post = vi.fn(),
    call = vi.fn(),
    api = { post, call } as unknown as API;
  const client = new EditorClient(api);
  client.set({
    snapshot: {
      id: "project",
      revision: "old",
      read_only: false,
      observations: [point],
      history: { undo: true, redo: true },
    } as Snapshot,
    lease: "lease",
  });
  return { client, post, call };
}
describe("revisioned core command adapter", () => {
  it("updates revision from committed backend snapshot", async () => {
    const { client, post } = session();
    post.mockResolvedValue({
      snapshot: { ...client.state.snapshot, revision: "new" },
    });
    await client.commands([
      { type: "MoveObservation", observation_id: "one", pixel: [110, 200] },
    ]);
    expect(client.state.snapshot?.revision).toBe("new");
    expect(post.mock.calls[0][1].expected_revision).toBe("old");
  });
  it("stops writes on conflict and never silently retries", async () => {
    const { client, post } = session();
    post.mockRejectedValue(new APIError(409, "external change"));
    await client.commands([
      { type: "MoveObservation", observation_id: "one", pixel: [1, 2] },
    ]);
    expect(client.state.conflict).toBe(true);
    await client.commands([
      { type: "DeleteObservation", observation_id: "one" },
    ]);
    expect(post).toHaveBeenCalledTimes(1);
  });
  it("reverts failed drag to reloaded canonical coordinates", async () => {
    const { client, post, call } = session();
    post.mockRejectedValue(new APIError(422, "invalid pixel"));
    call.mockResolvedValue({ ...client.state.snapshot, observations: [point] });
    expect(
      await client.commands([
        { type: "MoveObservation", observation_id: "one", pixel: [-5, 2] },
      ]),
    ).toBe(false);
    expect(client.state.snapshot?.observations[0]).toEqual(point);
  });
  it("commits one drag command rather than pointer moves", async () => {
    const { client, post } = session();
    post.mockResolvedValue({ snapshot: client.state.snapshot });
    await client.commands([
      { type: "MoveObservation", observation_id: "one", pixel: [120, 220] },
    ]);
    expect(post).toHaveBeenCalledTimes(1);
    expect(post.mock.calls[0][1].commands).toHaveLength(1);
  });
  it.each(["undo", "redo"])(
    "uses backend history for %s",
    async (operation) => {
      const { client, post } = session();
      post.mockResolvedValue({ snapshot: client.state.snapshot });
      await client.run(operation);
      expect(post.mock.calls[0][0]).toBe("/projects/project/" + operation);
    },
  );
  it("does not reclassify an own notification as a conflict", () => {
    const { client } = session();
    client.external("old");
    expect(client.state.conflict).toBe(false);
    client.external("external");
    expect(client.state.conflict).toBe(true);
  });
  it("never blocks canonical dragging while presentation preferences save", async () => {
    const { client, post } = session();
    let complete: (v: unknown) => void = () => {};
    post.mockImplementation(
      () =>
        new Promise((r) => {
          complete = r;
        }),
    );
    const pending = client.preferences({ active_view: "side" });
    expect(client.writable).toBe(true);
    expect(client.state.busy).toBe(false);
    complete({ snapshot: { revision: "ignored" } });
    await pending;
    expect(client.state.snapshot?.revision).toBe("old");
  });
  it("treats event cursors as hints and rechecks canonical revision", async () => {
    const { client, call } = session();
    call.mockResolvedValue({ revision: "old" });
    await client.reconcile();
    expect(client.state.conflict).toBe(false);
    call.mockResolvedValue({ revision: "external" });
    await client.reconcile();
    expect(client.state.conflict).toBe(true);
  });
  it("does not turn a lease renewal racing own edits into a conflict", async () => {
    const { client, post, call } = session();
    post.mockRejectedValue(new APIError(409, "stale renewal"));
    call.mockResolvedValue({ revision: "old" });
    await client.renew();
    expect(client.state.conflict).toBe(false);
  });
});
