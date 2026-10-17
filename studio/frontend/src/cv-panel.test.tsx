// @vitest-environment jsdom
import { it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
  act,
} from "@testing-library/react";
import { CVPanel } from "./CVPanel";
import type { AssistCanvas, CVProposal, AssistTool } from "./cv-types";
import type { EditorClient } from "./api";
import type { Snapshot } from "./types";
afterEach(cleanup);
function fixture(tool: AssistTool = "detect_wheels", available = true) {
  const snapshot = {
    id: "study",
    revision: "r1",
    roles: ["roof", "wheel"],
    references: [],
    editable: true,
  } as unknown as Snapshot;
  let canvas: AssistCanvas | undefined;
  let p = {
    proposal_id: "proposal",
    provider_id: "local",
    provider_version: "1",
    capability: "detect_wheels",
    source_revision: "r1",
    source_reference_id: "ref",
    source_sha256: "a".repeat(64),
    source_role: "multiview",
    source_size: [256, 256],
    crop: [16, 16, 240, 240],
    crop_id: "crop",
    view: "side",
    created_input_hash: "hash",
    parameters: { threshold: 140 },
    status: "ACTIVE",
    proposal_revision: 1,
    elapsed_ms: 12,
    cache_hit: false,
    warnings: ["Geometry only"],
    rasters: [],
    components: [0, 1].map((i) => ({
      id: "c" + i,
      kind: "circle",
      center: [50 + 100 * i, 100],
      radius_px: 20,
      semantic_role: "UNKNOWN",
      status: "ACTIVE",
      score: 0.8,
    })),
  } as CVProposal;
  const call = vi.fn(async (path: string) =>
    path === "/cv/providers"
      ? {
          providers: [
            {
              provider_id: "local",
              provider_version: "1",
              available,
              capabilities: [
                "smart_edge",
                "segment_object",
                "detect_wheels",
                "trace_contour",
                "detect_edges",
              ],
            },
          ],
        }
      : path.includes("cv-context")
        ? {
            crop: [16, 16, 240, 240],
            crop_id: "crop",
            source_sha256: "a".repeat(64),
          }
        : p,
  );
  const post = vi.fn(async (path: string, body: any) => {
    if (path.endsWith("cv-jobs")) {
      p = {
        ...p,
        proposal_id: "p" + post.mock.calls.length,
        capability: body.request.capability,
        parameters: body.request.parameters,
      };
      if (p.capability === "segment_object")
        p = { ...p, rasters: ["mask"], raster_bounds: [20, 30, 200, 210] };
      if (p.capability === "detect_edges")
        p = { ...p, rasters: ["edges"], raster_bounds: [16, 16, 240, 240] };
      return {
        job_id: "job",
        activity: "FINISHED",
        result: "SUCCEEDED",
        proposal_id: p.proposal_id,
      };
    }
    if (path.endsWith("/reject")) {
      p = { ...p, status: "REJECTED" };
      return p;
    }
    return p;
  });
  const run = vi.fn(async () => {
    p = { ...p, status: "ACCEPTED" };
    return true;
  });
  const client = {
    api: { call, post },
    run,
    writable: true,
    state: { conflict: false, lease: "lease" },
  } as unknown as EditorClient;
  const props = {
    snapshot,
    client,
    reference: {
      id: "ref",
      role: "multiview",
      size: [256, 256] as [number, number],
      sha256: "a".repeat(64),
    },
    view: "side" as const,
    initialTool: tool,
    activation: 1,
    onCanvas: (v: AssistCanvas | undefined) => {
      canvas = v;
    },
    onExit: vi.fn(),
  };
  const rendered = render(<CVPanel {...props} />);
  return {
    props,
    rendered,
    post,
    run,
    call,
    get canvas() {
      return canvas!;
    },
    async ready() {
      await waitFor(() => expect(canvas?.active).toBe(available));
    },
    async roi() {
      await act(async () => {
        canvas!.onDown([20, 30]);
      });
      await act(async () => {
        canvas!.onUp([200, 210]);
      });
      await screen.findByRole("heading", {
        name: "Proposal inspector · ACTIVE",
      });
    },
  };
}
it("directed Smart Edge waits for a start and publishes only a dashed transient layer", async () => {
  const f = fixture("smart_edge");
  await f.ready();
  expect(f.canvas.crop).toEqual([16, 16, 240, 240]);
  await act(async () => f.canvas.onDown([50, 60]));
  expect(f.post).not.toHaveBeenCalled();
  expect(f.run).not.toHaveBeenCalled();
  expect(f.canvas.preview).toEqual([[50, 60]]);
  expect(
    screen
      .getByRole("button", { name: "Finish trace" })
      .hasAttribute("disabled"),
  ).toBe(true);
  fireEvent.click(screen.getByLabelText("Visible · dashed"));
  expect(f.canvas.visible).toBe(false);
  expect(screen.getByText(/CV PROPOSAL ≠ source observation/)).toBeTruthy();
});
it("candidate semantics and explicit partial ACCEPT call only the canonical transaction bridge", async () => {
  const f = fixture();
  await f.ready();
  await f.roi();
  const accept = screen.getByRole("button", { name: "ACCEPT selected" });
  expect(accept.hasAttribute("disabled")).toBe(true);
  expect(f.run).not.toHaveBeenCalled();
  fireEvent.click(screen.getByLabelText("Select CV c0"));
  fireEvent.click(screen.getByLabelText("Select CV c1"));
  fireEvent.change(screen.getByLabelText("CV semantic role"), {
    target: { value: "wheel" },
  });
  fireEvent.click(accept);
  await waitFor(() => expect(f.run).toHaveBeenCalledTimes(1));
  expect(f.run.mock.calls[0]).toEqual([
    expect.stringContaining("/accept"),
    expect.objectContaining({
      component_ids: ["c1"],
      semantic_roles: { c1: "wheel" },
      confirm_observed: false,
    }),
  ]);
});
it("source change stales proposals; rejection and parameter RERUN never call canonical edits", async () => {
  const f = fixture();
  await f.ready();
  await f.roi();
  fireEvent.change(screen.getByLabelText("Edge Map threshold"), {
    target: { value: "210" },
  });
  await screen.findByRole("heading", { name: "Proposal inspector · STALE" });
  expect(
    screen
      .getByRole("button", { name: "ACCEPT selected" })
      .hasAttribute("disabled"),
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "RERUN" }));
  await screen.findByRole("heading", { name: "Proposal inspector · ACTIVE" });
  const request = f.post.mock.calls
    .filter((c) => c[0].endsWith("cv-jobs"))
    .at(-1)![1].request;
  expect(request.parameters.threshold).toBe(210);
  fireEvent.click(screen.getByRole("button", { name: "REJECT selected" }));
  await screen.findByRole("heading", { name: "Proposal inspector · REJECTED" });
  expect(f.run).not.toHaveBeenCalled();
  f.rendered.rerender(
    <CVPanel {...f.props} snapshot={{ ...f.props.snapshot, revision: "r2" }} />,
  );
  expect(f.run).not.toHaveBeenCalled();
});
it("mask brushes and diagnostic visibility modify proposal requests/layers without canonical writes", async () => {
  const f = fixture("magic_select");
  await f.ready();
  await f.roi();
  fireEvent.click(
    screen.getByRole("button", { name: "Foreground / Add region" }),
  );
  await act(async () => {
    f.canvas.onDown([50, 60]);
  });
  await act(async () => {
    f.canvas.onMove([55, 65], true);
    f.canvas.onUp([60, 70]);
  });
  await waitFor(() =>
    expect(
      screen.getByTestId("cv-panel").getAttribute("data-mask-strokes"),
    ).toBe("1"),
  );
  const requests = f.post.mock.calls.filter((c) => c[0].endsWith("cv-jobs"));
  expect(requests.at(-1)![1].request.parameters.strokes[0]).toMatchObject({
    label: "foreground",
    points: [
      [50, 60],
      [55, 65],
      [60, 70],
    ],
  });
  fireEvent.click(screen.getByRole("button", { name: "Update edge map" }));
  await waitFor(() =>
    expect(f.canvas.rasters.some((r) => r.url.endsWith("/edges"))).toBe(true),
  );
  fireEvent.click(screen.getByLabelText("Edge Map visible"));
  expect(f.canvas.rasters.some((r) => r.url.endsWith("/edges"))).toBe(false);
  expect(f.run).not.toHaveBeenCalled();
});
it("an unavailable provider leaves the manual exit available and assisted input inactive", async () => {
  const f = fixture("smart_edge", false);
  await f.ready();
  expect(screen.getByText(/Provider unavailable. Install/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Manual tools" }));
  expect(f.props.onExit).toHaveBeenCalledTimes(1);
  expect(f.post).not.toHaveBeenCalled();
  expect(f.run).not.toHaveBeenCalled();
});
it("an active proposal becomes stale when its pinned canonical source revision changes", async () => {
  const f = fixture();
  await f.ready();
  await f.roi();
  f.rendered.rerender(
    <CVPanel {...f.props} snapshot={{ ...f.props.snapshot, revision: "r2" }} />,
  );
  await screen.findByRole("heading", { name: "Proposal inspector · STALE" });
  expect(
    screen
      .getByRole("button", { name: "ACCEPT selected" })
      .hasAttribute("disabled"),
  ).toBe(true);
  expect(f.run).not.toHaveBeenCalled();
});
