import { test, expect, type Page } from "@playwright/test";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import {
  repo,
  python,
  server,
  boot,
  snapshot,
  camera,
  saved,
  rss,
} from "./harness";
const root = resolve(repo, "build/studio03-browser-" + Date.now(), "projects");
test.beforeAll(() => {
  const r = spawnSync(
    python,
    [resolve(repo, "studio/backend/tests/prepare_cv.py"), root],
    { cwd: repo, encoding: "utf8", windowsHide: true },
  );
  if (r.status !== 0) throw Error(r.stderr);
});
test.use({ deviceScaleFactor: 2 });
async function open(
  page: Page,
  name: string,
  running: Awaited<ReturnType<typeof server>>,
) {
  await boot(page, running);
  await page
    .getByRole("button", { name: new RegExp("▱ " + name + " ") })
    .click();
  await page.getByText("SOURCE PIXELS", { exact: true }).waitFor();
}
async function pixel(page: Page, p: number[]) {
  const box = (await page.getByTestId("canvas").boundingBox())!,
    v = await camera(page);
  return { x: box.x + v.x + p[0] * v.scale, y: box.y + v.y + p[1] * v.scale };
}
async function tool(page: Page, name: string) {
  await page
    .locator(".tool-bar")
    .getByRole("button", { name, exact: true })
    .click();
  await expect(page.getByTestId("cv-panel")).toBeVisible();
  await expect(page.getByTestId("canvas")).toHaveAttribute(
    "data-cv-active",
    "true",
  );
}
async function newProposal(page: Page, before: string) {
  const panel = page.getByTestId("cv-panel");
  await expect(panel).not.toHaveAttribute("data-proposal-id", before, {
    timeout: 30000,
  });
  await expect(panel).toHaveAttribute("data-busy", "false", { timeout: 30000 });
  await expect(panel).toHaveAttribute("data-proposal-status", "ACTIVE");
  return (await panel.getAttribute("data-proposal-id"))!;
}
async function proposal(page: Page, id: string) {
  return page.evaluate(async (id) => {
    const projects = await (await fetch("/api/v1/projects")).json();
    const selected = projects.find(
      (p: any) =>
        p.project?.asset_name ===
        document.querySelector(".project-bar strong")?.textContent,
    );
    return (
      await fetch(`/api/v1/projects/${selected.id}/cv-proposals/${id}`, {
        headers: { "X-Studio-Tab": sessionStorage.getItem("vr-tab")! },
      })
    ).json();
  }, id);
}
async function dragROI(page: Page, from: number[], to: number[]) {
  const a = await pixel(page, from),
    b = await pixel(page, to);
  await page.mouse.move(a.x, a.y);
  await page.mouse.down();
  await page.mouse.move(b.x, b.y, { steps: 8 });
  await page.mouse.up();
}
async function world(page: Page, name: string) {
  const s = await snapshot(page, name);
  return page.evaluate(
    async (id) => (await fetch(`/api/v1/projects/${id}/analysis`)).json(),
    s.id,
  );
}
function hash(path: string) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}
async function offline(page: Page, origin: string) {
  const blocked: { url: string; method: string; type: string }[] = [];
  await page.route("**/*", async (route) => {
    const r = route.request();
    if (/^https?:/.test(r.url()) && !r.url().startsWith(origin + "/")) {
      blocked.push({
        url: r.url(),
        method: r.method(),
        type: r.resourceType(),
      });
      await route.abort("internetdisconnected");
    } else await route.continue();
  });
  return () => {
    // Some Windows test machines inject this local antivirus script into HTTP.
    // It is blocked before transmission. Every other external attempt fails.
    expect(
      blocked.filter(
        (r) =>
          !(
            new URL(r.url).hostname === "me.kis.v2.scr.kaspersky-labs.com" &&
            r.method === "GET" &&
            r.type === "script"
          ),
      ),
    ).toEqual([]);
    return {
      external_attempts_blocked: blocked.length,
      source_image_egress: 0,
    };
  };
}

test("Smart Edge source pixels survive zoom/pan/DPR2, bounded fit, ACCEPT and exact undo", async ({
  page,
}) => {
  const running = await server(root),
    checkOffline = await offline(page, running.origin);
  try {
    await open(page, "cv_strong_edge", running);
    const before = await snapshot(page, "cv_strong_edge");
    await tool(page, "Smart Edge");
    const panel = page.getByTestId("cv-panel");
    await expect(page.getByTestId("canvas")).toHaveAttribute(
      "data-cv-crop",
      "[16,16,240,240]",
    );
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
    const box = (await page.getByTestId("canvas").boundingBox())!;
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down({ button: "middle" });
    await page.mouse.move(
      box.x + box.width / 2 + 28,
      box.y + box.height / 2 - 12,
      { steps: 4 },
    );
    await page.mouse.up({ button: "middle" });
    let at = await pixel(page, [127, 38]);
    await page.mouse.click(at.x, at.y);
    at = await pixel(page, [127, 100]);
    await page.mouse.move(at.x, at.y, { steps: 5 });
    await expect
      .poll(
        async () => Number(await panel.getAttribute("data-preview-samples")),
        { timeout: 20000 },
      )
      .toBeGreaterThan(0);
    await expect
      .poll(async () =>
        Number(
          await page
            .getByTestId("canvas")
            .getAttribute("data-cv-preview-points"),
        ),
      )
      .toBeGreaterThan(1);
    at = await pixel(page, [127, 190]);
    await page.mouse.click(at.x, at.y);
    const id = await newProposal(page, "");
    await expect
      .poll(async () => Number(await panel.getAttribute("data-commit-samples")))
      .toBe(1);
    expect((await snapshot(page, "cv_strong_edge")).revision).toBe(
      before.revision,
    );
    await panel
      .getByRole("button", { name: "Finish trace", exact: true })
      .click();
    await panel.getByLabel("CV fit spline").check();
    await panel.getByLabel("CV fit tolerance").fill("1");
    const oldRevision = (await proposal(page, id)).proposal_revision;
    await panel
      .getByRole("button", { name: "Simplify / Fit proposal", exact: true })
      .click();
    await expect
      .poll(async () => (await proposal(page, id)).proposal_revision)
      .toBeGreaterThan(oldRevision);
    const fitted = await proposal(page, id);
    expect(fitted.components[0].kind).toBe("spline");
    expect(
      fitted.components[0].fit.certified_max_deviation_px,
    ).toBeLessThanOrEqual(1);
    await expect(
      panel.getByRole("button", { name: "ACCEPT selected", exact: true }),
    ).toBeDisabled();
    await panel.getByLabel("CV semantic role").selectOption("roof");
    await panel
      .getByRole("button", { name: "ACCEPT selected", exact: true })
      .click();
    await saved(page);
    await expect
      .poll(
        async () =>
          (await snapshot(page, "cv_strong_edge")).observations.length,
      )
      .toBe(before.observations.length + 1);
    const after = await snapshot(page, "cv_strong_edge"),
      accepted = after.observations.find((o: any) => o.id.startsWith("cv_"));
    expect(accepted.view).toBe("side");
    expect(accepted.kind).toBe("spline");
    expect(accepted.visibility).toBe("inferred");
    expect(Math.abs(accepted.points[0].pixel[0] - 128)).toBeLessThan(5);
    expect(after.observations.filter((o: any) => o.view === "top")).toEqual(
      before.observations.filter((o: any) => o.view === "top"),
    );
    await page.getByRole("button", { name: "Undo", exact: true }).click();
    await saved(page);
    await expect
      .poll(async () => (await snapshot(page, "cv_strong_edge")).revision)
      .toBe(before.revision);
    checkOffline();
    await page.screenshot({
      path: resolve(repo, "build/studio03-smart-edge.png"),
    });
  } finally {
    await running.stop();
  }
});

test("Magic Select refines FG/BG mask, accepts one component and preserves original bytes", async ({
  page,
}) => {
  const running = await server(root),
    path = resolve(root, "cv_body_mask/input/reference.png"),
    beforeHash = hash(path);
  try {
    await open(page, "cv_body_mask", running);
    const before = await snapshot(page, "cv_body_mask");
    await tool(page, "Magic Select");
    const panel = page.getByTestId("cv-panel");
    await dragROI(page, [20, 42], [238, 210]);
    let id = await newProposal(page, "");
    const first = await proposal(page, id);
    expect(first.components.length).toBeGreaterThan(1);
    await panel
      .getByRole("button", { name: "Foreground / Add region", exact: true })
      .click();
    await dragROI(page, [130, 100], [140, 105]);
    id = await newProposal(page, id);
    const afterFG = await proposal(page, id);
    await panel
      .getByRole("button", { name: "Background / Remove region", exact: true })
      .click();
    await dragROI(page, [135, 130], [145, 132]);
    id = await newProposal(page, id);
    const corrected = await proposal(page, id);
    expect(corrected.mask.foreground_pixels).toBeLessThan(
      afterFG.mask.foreground_pixels,
    );
    await expect(panel).toHaveAttribute("data-mask-strokes", "2");
    expect((await snapshot(page, "cv_body_mask")).revision).toBe(
      before.revision,
    );
    await panel.getByLabel("CV semantic role").selectOption("hood");
    await panel
      .getByRole("button", { name: "ACCEPT selected", exact: true })
      .click();
    await saved(page);
    await expect
      .poll(
        async () => (await snapshot(page, "cv_body_mask")).observations.length,
      )
      .toBe(before.observations.length + 1);
    const decided = await proposal(page, id);
    expect(
      decided.components.filter((c: any) => c.status === "ACCEPTED"),
    ).toHaveLength(1);
    expect(decided.components.some((c: any) => c.status === "STALE")).toBe(
      true,
    );
    expect(hash(path)).toBe(beforeHash);
    await page.screenshot({
      path: resolve(repo, "build/studio03-magic-select.png"),
    });
  } finally {
    await running.stop();
  }
});

test("wheel candidates require confirmation and never move world axle geometry", async ({
  page,
}) => {
  const running = await server(root);
  try {
    await open(page, "cv_circle_wheels", running);
    const before = await snapshot(page, "cv_circle_wheels"),
      geometry = await world(page, "cv_circle_wheels");
    await tool(page, "Detect Wheels");
    await dragROI(page, [30, 100], [225, 195]);
    const panel = page.getByTestId("cv-panel"),
      id = await newProposal(page, "");
    const p = await proposal(page, id);
    expect(p.components).toHaveLength(2);
    expect((await snapshot(page, "cv_circle_wheels")).revision).toBe(
      before.revision,
    );
    await panel.getByLabel("CV semantic role").selectOption("wheel");
    await panel
      .getByRole("button", { name: "ACCEPT selected", exact: true })
      .click();
    await saved(page);
    await expect
      .poll(
        async () =>
          (await snapshot(page, "cv_circle_wheels")).observations.length,
      )
      .toBe(before.observations.length + 1);
    const after = await world(page, "cv_circle_wheels");
    expect(after.world_landmarks).toEqual(geometry.world_landmarks);
    expect(after.scene.wheel_geometry).toEqual(geometry.scene.wheel_geometry);
    const accepted = (
      await snapshot(page, "cv_circle_wheels")
    ).observations.find((o: any) => o.id.startsWith("cv_"));
    expect(accepted.kind).toBe("circle");
    expect(accepted.center[0]).toBeCloseTo(70, 0);
    await page.screenshot({ path: resolve(repo, "build/studio03-wheels.png") });
  } finally {
    await running.stop();
  }
});

test("external observation edit stales a proposal and the API rejects acceptance", async ({
  page,
}) => {
  const running = await server(root);
  try {
    await open(page, "cv_curved_contour", running);
    await tool(page, "Trace Contour");
    await dragROI(page, [20, 20], [238, 238]);
    const id = await newProposal(page, ""),
      p = await proposal(page, id),
      before = await snapshot(page, "cv_curved_contour");
    const path = resolve(root, "cv_curved_contour/generated/calibration.json"),
      cal = JSON.parse(readFileSync(path, "utf8"));
    const observation = cal.views.side.landmarks.observations[0];
    observation.pixel[0] += 1;
    observation.revision++;
    for (const link of cal.correspondences)
      if (link.observation_id === observation.id)
        link.observation_revision = observation.revision;
    writeFileSync(path, JSON.stringify(cal, null, 2) + "\n");
    await expect(page.getByTestId("cv-panel")).toHaveAttribute(
      "data-proposal-status",
      "STALE",
      { timeout: 15000 },
    );
    await expect(
      page
        .getByTestId("cv-panel")
        .getByRole("button", { name: "ACCEPT selected", exact: true }),
    ).toBeDisabled();
    const status = await page.evaluate(
      async ({ id, p, before }) => {
        const headers = {
          "Content-Type": "application/json",
          "X-Studio-Tab": sessionStorage.getItem("vr-tab")!,
        };
        const csrf = (await (await fetch("/api/v1/session")).json()).csrf;
        const current = await (
          await fetch("/api/v1/projects/" + before.id, { headers })
        ).json();
        return (
          await fetch(
            `/api/v1/projects/${before.id}/cv-proposals/${id}/accept`,
            {
              method: "POST",
              headers: {
                ...headers,
                "X-CSRF-Token": csrf,
                "If-Match": current.revision,
                "Idempotency-Key": crypto.randomUUID().replaceAll("-", ""),
              },
              body: JSON.stringify({
                expected_revision: current.revision,
                lease_id: "expired-evidence-must-not-apply",
                proposal_revision: p.proposal_revision,
                component_ids: [p.components[0].id],
                semantic_roles: { [p.components[0].id]: "roof" },
              }),
            },
          )
        ).status;
      },
      { id, p, before },
    );
    expect(status).toBe(409);
    expect(
      (await snapshot(page, "cv_curved_contour")).observations.length,
    ).toBe(before.observations.length);
  } finally {
    await running.stop();
  }
});

test("disabled provider leaves manual point authoring and offline UI intact", async ({
  page,
}) => {
  const running = await server(root, false),
    checkOffline = await offline(page, running.origin);
  try {
    await open(page, "cv_false_positive", running);
    const before = await snapshot(page, "cv_false_positive");
    await page
      .locator(".tool-bar")
      .getByRole("button", { name: "Smart Edge", exact: true })
      .click();
    await expect(
      page.getByText(/Provider unavailable\. Install the optional/),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Manual tools", exact: true })
      .click();
    await page.getByRole("button", { name: "+ Point", exact: true }).click();
    const at = await pixel(page, [80, 100]);
    await page.mouse.click(at.x, at.y);
    await saved(page);
    await expect
      .poll(
        async () =>
          (await snapshot(page, "cv_false_positive")).observations.length,
      )
      .toBe(before.observations.length + 1);
    checkOffline();
  } finally {
    await running.stop();
  }
});

test("measure bounded Smart Edge and mask/refinement on a representative 4K source", async ({
  page,
}) => {
  test.setTimeout(180000);
  const running = await server(root),
    checkOffline = await offline(page, running.origin);
  try {
    await open(page, "cv_performance", running);
    const before = await snapshot(page, "cv_performance");
    expect(before.references[0].size).toEqual([3840, 2160]);
    await tool(page, "Smart Edge");
    const panel = page.getByTestId("cv-panel");
    let at = await pixel(page, [500, 500]);
    await page.mouse.click(at.x, at.y);
    for (let i = 0; i < 8; i++) {
      const n = Number(await panel.getAttribute("data-preview-samples"));
      at = await pixel(page, [500, 560 + 40 * i]);
      await page.mouse.move(at.x, at.y, { steps: 3 });
      await expect
        .poll(
          async () => Number(await panel.getAttribute("data-preview-samples")),
          { timeout: 20000 },
        )
        .toBeGreaterThan(n);
    }
    for (let i = 0; i < 4; i++) {
      at = await pixel(page, [500, 950 + 120 * i]);
      await page.mouse.click(at.x, at.y);
      await expect
        .poll(
          async () => Number(await panel.getAttribute("data-commit-samples")),
          { timeout: 20000 },
        )
        .toBe(i + 1);
    }
    const previews = JSON.parse(
        (await panel.getAttribute("data-preview-times"))!,
      ),
      commits = JSON.parse((await panel.getAttribute("data-commit-times"))!);
    const smart = await proposal(
      page,
      (await panel.getAttribute("data-proposal-id"))!,
    );
    await tool(page, "Magic Select");
    const start = Date.now();
    await dragROI(page, [1200, 600], [3330, 1680]);
    let id = await newProposal(page, smart.proposal_id);
    const firstMs = Date.now() - start,
      mask = await proposal(page, id),
      refinements: number[] = [];
    for (const [label, a, b] of [
      ["Foreground / Add region", [2000, 1000], [2050, 1010]],
      ["Background / Remove region", [2100, 1200], [2140, 1210]],
    ] as [string, number[], number[]][]) {
      await panel.getByRole("button", { name: label, exact: true }).click();
      const began = Date.now();
      await dragROI(page, a, b);
      id = await newProposal(page, id);
      refinements.push(Date.now() - began);
    }
    await panel
      .getByRole("button", { name: "Update edge map", exact: true })
      .click();
    await expect(panel).toHaveAttribute("data-busy", "false", {
      timeout: 30000,
    });
    await expect(panel.getByLabel("Edge Map visible")).toBeChecked();
    await panel.getByLabel("Edge Map visible").uncheck();
    expect((await snapshot(page, "cv_performance")).revision).toBe(
      before.revision,
    );
    const percentile = (v: number[], p: number) =>
      [...v].sort((a, b) => a - b)[
        Math.min(v.length - 1, Math.floor(v.length * p))
      ];
    const report = {
      status: "PASS",
      source: [3840, 2160],
      dpr: 2,
      preview_samples: previews,
      commit_samples: commits,
      preview_p50_ms: percentile(previews, 0.5),
      preview_p95_ms: percentile(previews, 0.95),
      commit_p50_ms: percentile(commits, 0.5),
      commit_p95_ms: percentile(commits, 0.95),
      mask_first_display_ms: firstMs,
      mask_provider_ms: mask.elapsed_ms,
      refinement_display_ms: refinements,
      fit: smart.components[0].fit,
      mask_components: mask.components.length,
      canonical_revision_unchanged: true,
      backend_rss_bytes: rss(running.pid),
      offline: checkOffline(),
      note: "Preview includes coalescing/debounce, local HTTP and two animation frames; mask display includes pointer ROI gesture. Synthetic analytical 4K source, no real-time claim.",
    };
    writeFileSync(
      resolve(repo, "build/studio03-cv-performance.json"),
      JSON.stringify(report, null, 2) + "\n",
    );
    await page.screenshot({
      path: resolve(repo, "build/studio03-cv-performance.png"),
    });
  } finally {
    await running.stop();
  }
});
