import { test, expect } from "@playwright/test";
import { spawnSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { repo, python, server, boot, saved, rss } from "../e2e/harness";
test("100 canonical surface parameter edits with 27 meshes, bounded cache/history and browser GC", async ({
  page,
  context,
}) => {
  const root = resolve(
    repo,
    "build/studio05-browser-retention-" + Date.now(),
    "projects",
  );
  const prepared = spawnSync(
    python,
    [resolve(repo, "studio/backend/tests/prepare_surfaces.py"), root],
    { cwd: repo, encoding: "utf8", windowsHide: true },
  );
  expect(prepared.status, prepared.stderr).toBe(0);
  const running = await server(root);
  try {
    await boot(page, running);
    await page
      .locator(".project-card")
      .filter({ has: page.getByText("Dense_Surface_Study", { exact: true }) })
      .click();
    await page.getByRole("button", { name: "Surfaces", exact: true }).click();
    await page.getByRole("button", { name: "Generate coarse preview" }).click();
    await expect(page.getByTestId("surface-preview-status")).toHaveText(
      "CURRENT · PASS",
    );
    await page
      .getByRole("listitem")
      .filter({ hasText: "Grid panel 0" })
      .click();
    const cdp = await context.newCDPSession(page);
    await cdp.send("HeapProfiler.collectGarbage");
    const baseline = await cdp.send("Runtime.getHeapUsage");
    const backendBaseline = rss(running.pid);
    const samples = [];
    let peak = baseline.usedSize,
      backendPeak = backendBaseline;
    for (let i = 1; i <= 100; i++) {
      const z = i * 0.00001;
      await page.getByLabel("Parameter points", { exact: true }).fill(
        JSON.stringify([
          [0, 0, z],
          [1, 0, z],
          [1, 1, z],
          [0, 1, z],
        ]),
      );
      await page
        .getByRole("button", { name: "Apply points", exact: true })
        .click();
      await saved(page);
      await expect(page.getByTestId("surface-preview-status")).toContainText(
        "STALE",
      );
      await page
        .getByRole("button", { name: "Generate coarse preview" })
        .click();
      await expect(page.getByTestId("surface-preview-status")).toHaveText(
        "CURRENT · PASS",
      );
      const heap = await cdp.send("Runtime.getHeapUsage");
      peak = Math.max(peak, heap.usedSize);
      if (i % 10 === 0) {
        const memory = rss(running.pid);
        backendPeak = Math.max(backendPeak, memory);
        await cdp.send("HeapProfiler.collectGarbage");
        samples.push({
          edits: i,
          browser_heap_after_gc_bytes: (await cdp.send("Runtime.getHeapUsage"))
            .usedSize,
          backend_rss_bytes: memory,
        });
      }
    }
    await cdp.send("HeapProfiler.collectGarbage");
    const post = await cdp.send("Runtime.getHeapUsage");
    expect(
      Number(
        await page
          .getByTestId("surface-three-canvas")
          .getAttribute("data-mesh-count"),
      ),
    ).toBe(27);
    expect(post.usedSize - baseline.usedSize).toBeLessThan(32 * 1024 * 1024);
    const report = {
      status: "PASS",
      canonical_surface_edits: 100,
      patches: 27,
      browser_heap_bytes: {
        baseline: baseline.usedSize,
        peak,
        post_gc: post.usedSize,
      },
      backend_rss_bytes: {
        baseline: backendBaseline,
        sampled_peak: backendPeak,
        post_gc: rss(running.pid),
      },
      samples,
    };
    writeFileSync(
      resolve(repo, "build/studio05-surface-browser-retention.json"),
      JSON.stringify(report, null, 2),
    );
  } finally {
    await running.stop();
  }
});
