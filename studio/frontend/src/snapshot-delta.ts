import type { Observation, Snapshot } from "./types";
export type SnapshotDelta = {
  base_revision: string;
  revision: string;
  metadata: Omit<Snapshot, "observations">;
  upsert: Observation[];
  remove: string[];
  order: string[];
};
export function applySnapshotDelta(
  before: Snapshot,
  delta: SnapshotDelta,
): Snapshot {
  if (
    before.revision !== delta.base_revision ||
    before.id !== delta.metadata.id ||
    delta.revision !== delta.metadata.revision
  )
    throw new Error(
      "Incremental response belongs to a different project/revision",
    );
  const observations = new Map(before.observations.map((o) => [o.id, o]));
  for (const id of delta.remove) {
    if (!observations.delete(id))
      throw new Error("Missing removed entity in incremental response");
  }
  const updated = new Set<string>();
  for (const observation of delta.upsert) {
    if (updated.has(observation.id))
      throw new Error("Duplicate incremental entity");
    updated.add(observation.id);
    observations.set(observation.id, observation);
  }
  if (
    new Set(delta.order).size !== delta.order.length ||
    delta.order.length !== observations.size ||
    delta.order.some((id) => !observations.has(id))
  )
    throw new Error(
      "Incremental entity order does not match the canonical snapshot",
    );
  return {
    ...delta.metadata,
    observations: delta.order.map((id) => observations.get(id)!),
  };
}
