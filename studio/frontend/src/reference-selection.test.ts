import { expect, it } from "vitest";
import { activeReference, type Snapshot } from "./types";
const references = [
  { id: "a", role: "multiview", size: [100, 100], sha256: "a" },
  { id: "b", role: "control_overlay", size: [100, 100], sha256: "b" },
  { id: "c", role: "source_hash", size: [200, 100], sha256: "c" },
];
it("preserves manual reference selection for an existing study", () => {
  const snapshot = {
    references,
    views: { side: { reference_role: "multiview" } },
  } as unknown as Snapshot;
  expect(
    activeReference(snapshot, {
      active_view: "side",
      reference_id: "control_overlay",
    }),
  ).toBe(references[1]);
});
it("displays the replacement bound to a view even with older global preferences", () => {
  const snapshot = {
    references,
    views: {
      top: { reference_role: "source_hash" },
      side: { reference_role: "multiview" },
    },
  } as unknown as Snapshot;
  expect(
    activeReference(snapshot, {
      active_view: "top",
      reference_id: "multiview",
    }),
  ).toBe(references[2]);
  expect(
    activeReference(snapshot, {
      active_view: "side",
      reference_id: "multiview",
    }),
  ).toBe(references[0]);
});
