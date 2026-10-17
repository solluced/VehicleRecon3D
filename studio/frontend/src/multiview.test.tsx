// @vitest-environment jsdom
import { it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { MultiWorkspace } from "./MultiWorkspace";
import type { EditorClient } from "./api";
import type { Snapshot } from "./types";
import type { Analysis } from "./multiview-types";
vi.mock("./Canvas", () => ({
  SourceCanvas: ({ view, onSelect }: any) => (
    <button
      aria-label={"Pick " + view}
      onClick={() => onSelect({ entity: "obs_" + view })}
    >
      source pixels
    </button>
  ),
}));
vi.mock("./Preview3D", () => ({
  Preview3D: () => <div>Mock 3D renderer</div>,
}));
afterEach(cleanup);
function fixture() {
  const observation = {
    id: "obs_side",
    kind: "point",
    view: "side",
    semantic_role: "roof",
    pixel: [128, 78],
    reference_id: "multiview",
    source_sha256: "a".repeat(64),
    crop_id: "b".repeat(64),
    revision: 1,
    uncertainty_px: 1,
    visibility: "observed",
    measured: true,
    provenance: { type: "measured", method: "Analytical UI fixture" },
  };
  const snapshot = {
    id: "study",
    revision: "r1",
    version: 2,
    read_only: false,
    editable: true,
    project: {
      asset_name: "Study",
      project_id: "study",
      vehicle_profile: "sedan",
      dimensions: {},
    },
    observations: [observation],
    references: [
      {
        id: "ref",
        role: "multiview",
        size: [256, 256],
        sha256: "a".repeat(64),
      },
    ],
    roles: ["roof"],
    measurements: [],
    views: { side: { crop_id: { multiview: "b".repeat(64) } } },
    readiness: { surfaces: { state: "BLOCKED" } },
    history: { undo: false, redo: false },
    preferences: {},
  } as Snapshot;
  const analysis = {
    revision: "r1",
    read_only: false,
    views: Object.fromEntries(
      ["side", "top", "front", "rear"].map((v) => [
        v,
        {
          crop: [0, 0, 256, 256],
          calibrated: true,
          rectification: "NONE",
          coordinate_system: "RAW SOURCE PIXELS",
        },
      ]),
    ),
    residuals: {
      status: "PASS",
      rows: [
        {
          id: "link_side",
          observation_id: "obs_side",
          world_entity_id: "roof",
          binding_type: "landmark",
          view: "side",
          semantic_role: "roof",
          observed_pixel: [128, 78],
          projected_pixel: [128, 78],
          world: [0, 0.5, 1],
          residual_px: 0,
          allowed_tolerance_px: 2,
          status: "PASS",
          heat: "PASS",
          critical: true,
          required: true,
          inferred: false,
        },
      ],
      summary: {},
    },
    heat_policy: {
      near_ratio: 0.8,
      fail_ratio: 1,
      metric: "residual / tolerance",
    },
    coverage: [
      {
        entity_id: "roof",
        views: { side: 1, top: 0, front: 0, rear: 0 },
        semantic_roles: ["roof"],
      },
    ],
    groups: [],
    correspondences: [],
    world_landmarks: { roof: [0, 0.5, 1] },
    scene: {
      landmarks: { roof: [0, 0.5, 1] },
      controls: [],
      curves: [],
      axes: { X: "longitudinal", Y: "lateral", Z: "up" },
      units: "m",
    },
    policy: {
      coverage_confirmed: true,
      critical_correspondence_ids: ["link_side"],
      required_views: ["side"],
      required_proofs: [],
    },
    reviews: {
      source: {
        subject: "c".repeat(64),
        status: {
          state: "BLOCKED",
          decision: "NEEDS_CORRECTION",
          current: true,
          reasons: [],
        },
        record: null,
      },
      cage: {
        subject: "d".repeat(64),
        status: {
          state: "BLOCKED",
          decision: "NEEDS_CORRECTION",
          current: true,
          reasons: [],
        },
        record: null,
      },
    },
    wheelbase: {
      world_wheelbase_m: 2,
      authoritative_wheelbase_m: 2,
      difference_m: 0,
      authority: {},
    },
    ratios: { status: "NOT ENOUGH DATA", rows: [] },
    rectification_candidates: [],
    dimensions: {},
    input_identities: { multiview: "a".repeat(64) },
  } as Analysis;
  const commands = vi.fn().mockResolvedValue(true),
    run = vi.fn().mockResolvedValue(true),
    client = {
      api: { call: vi.fn().mockResolvedValue(analysis) },
      writable: true,
      state: { snapshot, lease: "lease", conflict: false },
      commands,
      run,
    } as unknown as EditorClient;
  render(
    <MultiWorkspace
      snapshot={snapshot}
      client={client}
      preferences={{}}
      onPreference={vi.fn()}
    />,
  );
  return { client, commands, run };
}
it("keeps source/world moves explicit and disables world modification in source mode", async () => {
  const { commands } = fixture();
  await screen.findByRole("button", { name: "Pick side" });
  fireEvent.click(screen.getByRole("button", { name: "Pick side" }));
  fireEvent.click(screen.getByRole("button", { name: /^World$/ }));
  expect(
    (
      screen.getByRole("button", {
        name: "Apply world XYZ",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Move World Landmark" }));
  fireEvent.change(screen.getByLabelText("World X"), {
    target: { value: "0.2" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Apply world XYZ" }));
  expect(commands.mock.calls[0][0][0]).toMatchObject({
    type: "MoveWorldLandmark",
    world_entity_id: "roof",
    point: [0.2, 0.5, 1],
  });
});
it("never auto-accepts reviews and submits the inspected subject with reviewer and note", async () => {
  const { run } = fixture();
  await screen.findByRole("button", { name: "Pick side" });
  fireEvent.click(screen.getByRole("button", { name: /^Review$/ }));
  expect(run).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Review decision"), {
    target: { value: "ACCEPTED" },
  });
  expect(
    (
      screen.getByRole("button", {
        name: "Record source decision",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  fireEvent.change(screen.getByLabelText("Reviewer"), {
    target: { value: "Human" },
  });
  fireEvent.change(screen.getByLabelText("Review note"), {
    target: { value: "Inspected independent evidence" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Record source decision" }),
  );
  expect(run).toHaveBeenCalledWith(
    "source-review",
    expect.objectContaining({
      decision: "ACCEPTED",
      reviewer: "Human",
      expected_subject: "c".repeat(64),
    }),
  );
});
it("shows four independent source viewports with coverage and declared tolerance", async () => {
  fixture();
  await screen.findByRole("button", { name: "Pick rear" });
  expect(screen.getAllByRole("button", { name: /^Pick / })).toHaveLength(4);
  expect(
    screen.getByRole("table", { name: "Semantic view coverage" }),
  ).toBeTruthy();
  expect(screen.getByText("0.00 / 2 px")).toBeTruthy();
});
