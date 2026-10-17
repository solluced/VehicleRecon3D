import { it, expect } from "vitest";
import { applySnapshotDelta, type SnapshotDelta } from "./snapshot-delta";
import type { Snapshot, Observation } from "./types";
const a = { id: "a", kind: "point", pixel: [1, 2] } as Observation;
const b = { id: "b", kind: "point", pixel: [3, 4] } as Observation;
const before = {
  id: "study",
  revision: "r1",
  observations: [a, b],
} as Snapshot;
const delta: SnapshotDelta = {
  base_revision: "r1",
  revision: "r2",
  metadata: { id: "study", revision: "r2" } as SnapshotDelta["metadata"],
  upsert: [{ ...a, pixel: [5, 6] } as Observation],
  remove: ["b"],
  order: ["a"],
};
it("merges validated changed entities in exact canonical order", () => {
  expect(applySnapshotDelta(before, delta)).toEqual({
    ...delta.metadata,
    observations: delta.upsert,
  });
  expect(before.observations).toEqual([a, b]);
});
it("fences wrong revisions, project identities and missing/duplicate entities", () => {
  expect(() =>
    applySnapshotDelta({ ...before, revision: "other" }, delta),
  ).toThrow();
  expect(() =>
    applySnapshotDelta(before, {
      ...delta,
      metadata: { ...delta.metadata, id: "other" },
    }),
  ).toThrow();
  expect(() =>
    applySnapshotDelta(before, { ...delta, order: ["a", "a"] }),
  ).toThrow();
  expect(() =>
    applySnapshotDelta(before, { ...delta, remove: ["missing"] }),
  ).toThrow();
  expect(() =>
    applySnapshotDelta(before, { ...delta, upsert: [a, a] }),
  ).toThrow();
});
