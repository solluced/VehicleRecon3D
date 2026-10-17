// @vitest-environment jsdom
import { afterEach, it, expect, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { SurfaceWorkspace } from "./SurfaceWorkspace";
import {
  previewCurrent,
  type SurfaceContext,
  type SurfacePreview,
} from "./surface-types";
import type { EditorClient } from "./api";
import type { Snapshot } from "./types";
vi.mock("./SurfacePreview3D", () => ({
  SurfacePreview3D: () => <div>Three.js adapter</div>,
}));
afterEach(cleanup);
function setup(accepted = true) {
  const context: SurfaceContext = {
    revision: "r1",
    evaluation_allowed: accepted,
    gate: accepted ? "READY" : "BLOCKED BY SOURCE/CAGE ACCEPTANCE",
    cage_boundaries: [],
    validation: [],
    graph: {
      schema_version: 2,
      nodes: [
        {
          id: "stable.sample",
          op: "coons",
          parameters: { bottom: "bottom" },
          dependencies: ["bottom"],
          draft: true,
        },
      ],
      patches: [
        {
          id: "stable.panel",
          name: "Panel",
          sample: "stable.sample",
          resolution: [8, 8],
          settings: {},
        },
      ],
    },
  };
  const catalog = {
    operations: [
      {
        id: "coons",
        version: 1,
        description: "Core Coons",
        required_inputs: ["bottom", "top"],
        optional_inputs: ["left", "right"],
        parameter_schema: {
          properties: { corner_tolerance: { type: "number", minimum: 0 } },
          required: [],
        },
        output_type: "surface",
        preview_supported: true,
        topology_supported: true,
      },
    ],
    capabilities: {
      support_rows: "Explicit schedules; no strength parameter",
      patch_boundary_extraction: false,
    },
  };
  const preview = {
    revision: "r1",
    status: "PASS",
    certified_current: true,
    patches: [],
    corners: {},
    adjacency: [],
    validation: [],
    generation_ms: 2,
    sampled_patches: [],
    quality: "low",
    label: "COARSE AUTHORING PREVIEW",
  } as unknown as SurfacePreview;
  const commands = vi.fn(async (_commands: Record<string, unknown>[]) => true),
    post = vi.fn(async () => preview),
    client = {
      writable: true,
      state: { conflict: false },
      commands,
      api: {
        call: vi.fn(async (path: string) =>
          path === "/surface-operations" ? catalog : context,
        ),
        post,
      },
    } as unknown as EditorClient;
  const snapshot = { id: "study", revision: "r1" } as Snapshot;
  return { context, client, snapshot, commands, post };
}
it("shows hard gate while still allowing explicit canonical drafts", async () => {
  const f = setup(false);
  render(<SurfaceWorkspace snapshot={f.snapshot} client={f.client} />);
  await screen.findByText("BLOCKED BY SOURCE/CAGE ACCEPTANCE");
  expect(
    (
      screen.getByRole("button", {
        name: "Generate coarse preview",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Add patch draft" }));
  await waitFor(() => expect(f.commands).toHaveBeenCalled());
  expect(f.commands.mock.calls[0][0][0]).toMatchObject({
    type: "AddSurfacePatch",
    op: "coons",
    semantic_role: "panel",
  });
  expect(f.commands.mock.calls[0][0][0].patch_id).toMatch(/^patch\./);
});
it("shares stable selection across list and schema properties, with typed reversal", async () => {
  const f = setup();
  render(<SurfaceWorkspace snapshot={f.snapshot} client={f.client} />);
  fireEvent.click(await screen.findByRole("listitem"));
  expect(screen.getByLabelText("Parameter corner_tolerance")).toBeTruthy();
  expect(screen.getByLabelText("Boundary bottom")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Reverse bottom" }));
  await waitFor(() =>
    expect(f.commands).toHaveBeenCalledWith([
      {
        type: "ReverseSurfaceBoundary",
        node_id: "stable.sample",
        boundary: "bottom",
      },
    ]),
  );
  expect(
    screen.getByText("Explicit schedules; no strength parameter"),
  ).toBeTruthy();
});
it("marks old mesh stale after a canonical revision change", async () => {
  const f = setup(),
    view = render(<SurfaceWorkspace snapshot={f.snapshot} client={f.client} />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Generate coarse preview" }),
  );
  await screen.findByText("CURRENT · PASS");
  f.context.revision = "r2";
  view.rerender(
    <SurfaceWorkspace
      snapshot={{ ...f.snapshot, revision: "r2" }}
      client={f.client}
    />,
  );
  await screen.findByText("STALE — regenerate after current reviews");
  expect(
    previewCurrent(
      { revision: "r1", certified_current: true } as SurfacePreview,
      "r2",
    ),
  ).toBe(false);
});
