// @vitest-environment jsdom
import { afterEach, it, expect, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { RectificationWorkspace } from "./RectificationWorkspace";
import type { Candidate, ReconciliationContext } from "./reconciliation-types";
import type { EditorClient } from "./api";
import type { Snapshot } from "./types";
afterEach(cleanup);
const request = {
  view: "top" as const,
  gauge_view: "side" as const,
  reference_role: "multiview",
  axis: "u" as const,
  image_domain_px: [0, 100],
  affine_domain_px: [0, 100],
  max_scale_change: 0.1,
  allow_extrapolation: false,
  anchors: [
    {
      id: "front",
      semantic: "front_axle",
      image: 0,
      world_normalized: 0,
      role: "FIT" as const,
      locked: true,
      confidence: 1,
      provenance: "exact",
    },
    {
      id: "feature",
      semantic: "roof",
      image: 0.5,
      world_normalized: 0.51,
      role: "HELD_OUT" as const,
      locked: false,
      confidence: 1,
      provenance: "measured",
      observation_id: "obs",
    },
    {
      id: "rear",
      semantic: "rear_axle",
      image: 1,
      world_normalized: 1,
      role: "FIT" as const,
      locked: true,
      confidence: 1,
      provenance: "exact",
    },
  ],
};
function setup(state = "ELIGIBLE_FOR_ACTIVATION", readonly = false) {
  const p: Candidate = {
    id: "a".repeat(32),
    revision: 1,
    status: state,
    active: false,
    freshness: state === "STALE" ? "STALE" : "current",
    creator: "Inspector",
    view: "top",
    source_revision: "r1",
    request,
    report: {
      eligible: state === "ELIGIBLE_FOR_ACTIVATION",
      status: state,
      distortion: state === "REJECTED" ? "EXCESSIVE" : "SMALL / ACCEPTABLE",
      reasons: state === "REJECTED" ? ["OUTSIDE SCALE LIMIT"] : [],
      strictly_monotonic: true,
      derivative_positive: true,
      foldover: false,
      anchors: request.anchors,
      allowed_scale: [0.9, 1.1],
      local_scale_range: [0.95, 1.05],
      samples: [
        {
          x: 0,
          y: 0,
          correction: 0,
          correction_px: 0,
          equivalent_mm: 0,
          derivative: 1,
          source_px: 0,
          target_px: 0,
          extrapolated: false,
        },
        {
          x: 1,
          y: 1,
          correction: 0,
          correction_px: 0,
          equivalent_mm: 0,
          derivative: 1,
          source_px: 100,
          target_px: 100,
          extrapolated: false,
        },
      ],
      held_out: [
        {
          id: "h",
          semantic: "roof",
          pixel: [50, 50],
          projected_affine: [51, 50],
          raw_residual_px: 1,
          rectified_residual_px: 0,
          tolerance_px: 1,
          delta_px: -1,
          status: "PASS",
        },
      ],
    },
  };
  const context: ReconciliationContext = {
    read_only: readonly,
    default_request: request,
    revision: "r1",
    calibration: { crop: [0, 0, 100, 100] },
    references: [
      { id: "ref", role: "multiview", size: [100, 100], sha256: "h" },
    ],
    candidates: [p],
  };
  const call = vi
      .fn()
      .mockImplementation((url: string) =>
        Promise.resolve(url.endsWith(p.id) ? p : context),
      ),
    post = vi
      .fn()
      .mockImplementation((url: string) =>
        Promise.resolve(
          url.endsWith("/reject") ? { ...p, status: "REJECTED" } : p,
        ),
      ),
    run = vi.fn().mockResolvedValue(true);
  const client = {
    api: { call, post },
    writable: !readonly,
    run,
  } as unknown as EditorClient;
  const snapshot = {
    id: "study",
    revision: "r1",
    read_only: readonly,
    references: context.references,
    observations: [],
    history: { undo: false },
  } as unknown as Snapshot;
  render(<RectificationWorkspace snapshot={snapshot} client={client} />);
  return { p, post, run };
}
it("edits manual anchors, respects exact locks and does not write canonical state on generation", async () => {
  const { post, run } = setup();
  await screen.findByLabelText("Semantic 1");
  expect(
    (screen.getByLabelText("Source normalized 0") as HTMLInputElement).disabled,
  ).toBe(true);
  fireEvent.change(screen.getByLabelText("Semantic 1"), {
    target: { value: "changed roof" },
  });
  fireEvent.change(screen.getByLabelText("Anchor role 1"), {
    target: { value: "FIT" },
  });
  fireEvent.change(screen.getByLabelText("Source normalized 1"), {
    target: { value: ".48" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Add anchor" }));
  await screen.findByLabelText("Semantic 3");
  fireEvent.click(screen.getByLabelText("Remove anchor 3"));
  fireEvent.change(screen.getByLabelText("Candidate creator"), {
    target: { value: "Author" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Generate Candidate" }));
  await waitFor(() => expect(post).toHaveBeenCalled());
  expect(post.mock.calls[0][1].request.anchors[1]).toMatchObject({
    semantic: "changed roof",
    role: "FIT",
    image: 0.48,
  });
  expect(run).not.toHaveBeenCalled();
});
it("renders authoritative graphs, limit text, preview, comparison and gates explicit activation", async () => {
  const { run, p } = setup();
  await screen.findByLabelText("Semantic 1");
  fireEvent.click(
    screen.getByRole("button", { name: `Inspect ${p.id.slice(0, 8)}` }),
  );
  await screen.findByRole("img", { name: "Mapping graph" });
  expect(screen.getByRole("img", { name: "Correction graph" })).toBeTruthy();
  expect(
    screen.getByRole("img", { name: "Derivative / local-scale graph" }),
  ).toBeTruthy();
  expect(screen.getByText(/Allowed 0.900000/)).toBeTruthy();
  expect(screen.getByLabelText("raw preview")).toBeTruthy();
  expect(screen.getByLabelText("rectified preview")).toBeTruthy();
  expect(
    screen.getByLabelText("Held-out residual report").textContent,
  ).toContain("PASS");
  const activate = screen.getByRole("button", {
    name: "ACTIVATE RECTIFICATION",
  }) as HTMLButtonElement;
  expect(activate.disabled).toBe(true);
  fireEvent.click(screen.getByLabelText("Confirm rectification activation"));
  expect(activate.disabled).toBe(false);
  fireEvent.click(activate);
  await waitFor(() =>
    expect(run).toHaveBeenCalledWith(
      "activate-rectification",
      expect.objectContaining({ candidate_id: p.id, confirm_activation: true }),
    ),
  );
  fireEvent.click(screen.getByLabelText(`Compare ${p.id}`));
  await screen.findByLabelText("Candidate comparison");
  fireEvent.change(screen.getByLabelText("Preview mode"), {
    target: { value: "difference" },
  });
  expect(screen.getByLabelText("difference preview")).toBeTruthy();
});
it("requires a rejection reason and keeps stale activation disabled", async () => {
  const { p, post } = setup("STALE");
  await screen.findByLabelText("Semantic 1");
  fireEvent.click(
    screen.getByRole("button", { name: `Inspect ${p.id.slice(0, 8)}` }),
  );
  await screen.findByLabelText("Candidate decision");
  fireEvent.click(screen.getByLabelText("Confirm rectification activation"));
  expect(
    (
      screen.getByRole("button", {
        name: "ACTIVATE RECTIFICATION",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  fireEvent.change(screen.getByLabelText("Rejection reason"), {
    target: { value: "Source changed" },
  });
  fireEvent.click(screen.getByRole("button", { name: "REJECT CANDIDATE" }));
  await waitFor(() =>
    expect(post).toHaveBeenCalledWith(expect.stringContaining("/reject"), {
      candidate_revision: 1,
      reason: "Source changed",
    }),
  );
});
it("presents read-only Mark II rejection without an activation override", async () => {
  setup("REJECTED", true);
  await screen.findByLabelText("Candidate decision");
  expect(screen.getByLabelText("Candidate decision").textContent).toContain(
    "REJECTED · NOT ACTIVE",
  );
  expect(screen.getByLabelText("Candidate decision").textContent).toContain(
    "OUTSIDE SCALE LIMIT",
  );
  expect(
    (
      screen.getByRole("button", {
        name: "ACTIVATE RECTIFICATION",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  expect(
    screen.queryByRole("button", { name: "Generate Candidate" }),
  ).toBeNull();
});
