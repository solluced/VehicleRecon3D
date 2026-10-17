import { test, expect } from "@playwright/test";
import { resolve } from "node:path";
import { writeFileSync } from "node:fs";
import { cpus, totalmem } from "node:os";
import {
  repo,
  prepare,
  server,
  boot,
  snapshot,
  camera,
  saved,
  rss,
} from "./harness";
const root = resolve(
  repo,
  "build/studio-v01b-performance-" + Date.now(),
  "projects",
);
test.beforeAll(() => prepare(root, true));
test("measure 4K, 5000 canonical controls and 20 display layers", async ({
  page,
  context,
}) => {
  test.setTimeout(240000);
  const running = await server(root);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  try {
    await boot(page, running);
    const began = Date.now();
    await page.getByRole("button", { name: /performance/ }).click();
    await page.getByText("SOURCE PIXELS", { exact: true }).waitFor();
    const displayMs = Date.now() - began;
    await expect(page.locator(".layer")).toHaveCount(20);
    const s = await snapshot(page, "performance");
    expect(s.observations).toHaveLength(5000);
    expect(s.references[0].size).toEqual([3840, 2160]);
    const cdp = await context.newCDPSession(page);
    await cdp.send("HeapProfiler.collectGarbage");
    const before = (await cdp.send("Runtime.getHeapUsage")).usedSize,
      backendBefore = rss(running.pid);
    await page.getByRole("button", { name: "↔ Pan", exact: true }).click();
    const measure = async (mode: string) =>
      page.evaluate(async (mode) => {
        const container = document.querySelector<HTMLElement>(
            '[data-testid="canvas"]',
          )!,
          content = container.querySelector<HTMLElement>(".konvajs-content")!,
          box = content.getBoundingClientRect();
        const x = box.left + box.width * 0.5,
          y = box.top + box.height * 0.5;
        const frames: number[] = [],
          draws: number[] = [];
        let previous = performance.now();
        if (mode === "pan")
          content.dispatchEvent(
            new MouseEvent("mousedown", {
              clientX: x,
              clientY: y,
              button: 0,
              buttons: 1,
              bubbles: true,
            }),
          );
        for (let i = 0; i < 120; i++) {
          await new Promise<void>(requestAnimationFrame as any);
          const now = performance.now();
          if (i > 5) frames.push(now - previous);
          previous = now;
          if (mode === "pan")
            content.dispatchEvent(
              new MouseEvent("mousemove", {
                clientX: x + Math.sin(i / 30) * 80,
                clientY: y + Math.cos(i / 30) * 30,
                buttons: 1,
                bubbles: true,
              }),
            );
          else
            content.dispatchEvent(
              new WheelEvent("wheel", {
                clientX: x,
                clientY: y,
                deltaY: i < 60 ? -5 : 5,
                bubbles: true,
                cancelable: true,
              }),
            );
          draws.push(Number(container.dataset.drawMs || 0));
        }
        if (mode === "pan")
          content.dispatchEvent(
            new MouseEvent("mouseup", {
              clientX: x,
              clientY: y,
              button: 0,
              bubbles: true,
            }),
          );
        const percentile = (v: number[], p: number) =>
          [...v].sort((a, b) => a - b)[
            Math.min(v.length - 1, Math.floor(v.length * p))
          ];
        return {
          samples: frames.length,
          frame_p50_ms: percentile(frames, 0.5),
          frame_p95_ms: percentile(frames, 0.95),
          draw_p95_ms: percentile(draws, 0.95),
          fps: 1000 / (frames.reduce((a, b) => a + b, 0) / frames.length),
        };
      }, mode);
    const pan = await measure("pan"),
      zoom = await measure("zoom");
    await page.getByRole("button", { name: "Fit", exact: true }).click();
    await page.getByRole("button", { name: "↖ Select", exact: true }).click();
    const canvas = page.getByTestId("canvas");
    const picking: number[] = [];
    await page.evaluate(() => {
      const state = window as unknown as {
        selectionTimes: number[];
      };
      state.selectionTimes = [];
    });
    for (const i of [1020, 2030, 3040, 4050, 1060, 2070, 3080, 4090]) {
      const o = s.observations[i],
        v = await camera(page),
        box = (await canvas.boundingBox())!;
      expect(
        await page.evaluate(
          () =>
            document.querySelector<HTMLInputElement>('[aria-label="Stable ID"]')
              ?.value,
        ),
      ).not.toBe(o.id);
      await page.evaluate((expected) => {
        document.querySelector('[data-testid="canvas"]')!.addEventListener(
          "mousedown",
          () => {
            const began = performance.now();
            const visible = () => {
              if (
                document.querySelector<HTMLInputElement>(
                  '[aria-label="Stable ID"]',
                )?.value === expected
              ) {
                (
                  window as unknown as { selectionTimes: number[] }
                ).selectionTimes.push(performance.now() - began);
              } else if (performance.now() - began < 30000) {
                requestAnimationFrame(visible);
              }
            };
            requestAnimationFrame(visible);
          },
          { once: true, capture: true },
        );
      }, o.id);
      await page.mouse.click(
        box.x + v.x + o.pixel[0] * v.scale,
        box.y + v.y + o.pixel[1] * v.scale,
      );
      picking.push(Number(await canvas.getAttribute("data-pick-ms")));
      // Measure every visible selection before dispatching the next click.
      // Otherwise React can coalesce rapid CDP clicks on a slower CI renderer.
      await expect(page.getByLabel("Stable ID", { exact: true })).toHaveValue(
        o.id,
      );
      await expect
        .poll(
          () =>
            page.evaluate(
              () =>
                (window as unknown as { selectionTimes: number[] })
                  .selectionTimes.length,
            ),
          { timeout: 30000 },
        )
        .toBe(picking.length);
    }
    await expect
      .poll(() =>
        page.evaluate(
          () =>
            (window as unknown as { selectionTimes: number[] }).selectionTimes
              .length,
        ),
      )
      .toBe(8);
    const selectionTimes = await page.evaluate(
      () => (window as unknown as { selectionTimes: number[] }).selectionTimes,
    );
    const chosen = await page
      .getByLabel("Stable ID", { exact: true })
      .inputValue();
    const point = s.observations.find((o: any) => o.id === chosen),
      v = await camera(page),
      box = (await canvas.boundingBox())!;
    await saved(page);
    const dragFrames = await page.evaluate(
      async ({ x, y }) => {
        const container = document.querySelector<HTMLElement>(
            '[data-testid="canvas"]',
          )!,
          content = container.querySelector<HTMLElement>(".konvajs-content")!;
        content.dispatchEvent(
          new MouseEvent("mousedown", {
            clientX: x,
            clientY: y,
            button: 0,
            buttons: 1,
            bubbles: true,
          }),
        );
        let last = performance.now();
        const frames: number[] = [];
        for (let i = 0; i < 90; i++) {
          await new Promise<void>(requestAnimationFrame as any);
          const now = performance.now();
          if (i > 5) frames.push(now - last);
          last = now;
          content.dispatchEvent(
            new MouseEvent("mousemove", {
              clientX: x + i * 0.4,
              clientY: y + Math.sin(i / 20) * 8,
              buttons: 1,
              bubbles: true,
            }),
          );
        }
        content.dispatchEvent(
          new MouseEvent("mouseup", {
            clientX: x + 36,
            clientY: y,
            button: 0,
            bubbles: true,
          }),
        );
        return frames.sort((a, b) => a - b)[Math.floor(frames.length * 0.95)];
      },
      {
        x: box.x + v.x + point.pixel[0] * v.scale,
        y: box.y + v.y + point.pixel[1] * v.scale,
      },
    );
    await saved(page);
    const commits: number[] = [];
    for (let i = 0; i < 8; i++) {
      await page
        .getByLabel("Uncertainty (px)", { exact: true })
        .fill(String(2 + i));
      const started = Date.now();
      await page.getByRole("button", { name: "Apply properties" }).click();
      await expect
        .poll(
          async () =>
            Number(
              await page
                .getByLabel("Uncertainty (px)", { exact: true })
                .inputValue(),
            ),
          { timeout: 30000 },
        )
        .toBe(2 + i);
      // Wait for the real transaction response, rather than the local form value.
      await expect(page.locator(".save-state")).toHaveText("Saved", {
        timeout: 30000,
      });
      await expect
        .poll(
          async () =>
            (await snapshot(page, "performance")).observations.find(
              (o: any) => o.id === chosen,
            ).uncertainty_px,
          { timeout: 30000 },
        )
        .toBe(2 + i);
      commits.push(Date.now() - started);
    }
    await cdp.send("HeapProfiler.collectGarbage");
    const after = (await cdp.send("Runtime.getHeapUsage")).usedSize;
    const percentile = (v: number[], p: number) =>
      [...v].sort((a, b) => a - b)[Math.floor(v.length * p)];
    const report = {
      status: "PASS",
      image: [3840, 2160],
      canonical_entities: 5000,
      display_layers: 20,
      device_pixel_ratio: await page.evaluate(() => devicePixelRatio),
      viewport: page.viewportSize(),
      browser: await page.evaluate(() => navigator.userAgent),
      cpu: cpus()[0].model,
      logical_cpus: cpus().length,
      system_memory_bytes: totalmem(),
      input:
        "Scripted browser pointer/wheel events through production Konva handlers; canonical property edits via visible UI",
      first_editor_display_ms: displayMs,
      pan,
      zoom,
      drag_frame_p95_ms: dragFrames,
      picking_p95_ms: percentile(picking, 0.95),
      selection_visible_p95_ms: percentile(selectionTimes, 0.95),
      repeated_real_edits: 8,
      commit_with_verification_p95_ms: percentile(commits, 0.95),
      browser_heap_before_bytes: before,
      browser_heap_after_gc_bytes: after,
      browser_heap_growth_bytes: after - before,
      backend_rss_before_bytes: backendBefore,
      backend_rss_after_bytes: rss(running.pid),
      browser_errors: errors,
    };
    writeFileSync(
      resolve(repo, "build/studio-v01b-performance.json"),
      JSON.stringify(report, null, 2),
    );
    await page.screenshot({
      path: resolve(repo, "build/studio-v01b-performance.png"),
    });
    expect(errors).toEqual([]);
    expect(report.picking_p95_ms).toBeLessThan(20);
    expect(pan.draw_p95_ms).toBeLessThan(100);
    expect(zoom.draw_p95_ms).toBeLessThan(100);
  } finally {
    await running.stop();
  }
});
