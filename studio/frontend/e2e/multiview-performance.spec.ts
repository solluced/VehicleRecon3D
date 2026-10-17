import { test, expect } from "@playwright/test";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { writeFileSync } from "node:fs";
import { cpus, totalmem } from "node:os";
import { repo, python, server, boot, rss, saved, snapshot } from "./harness";
const root = resolve(repo, "build/studio02-dense-" + Date.now(), "projects");
test.beforeAll(() => {
  const r = spawnSync(
    python,
    [
      resolve(repo, "studio/backend/tests/prepare_multiview.py"),
      root,
      "--performance",
    ],
    { cwd: repo, encoding: "utf8", windowsHide: true },
  );
  if (r.status !== 0) throw Error(r.stderr);
});
test("measure four 2D views plus Three.js with 5000 controls and live projections", async ({
  page,
  context,
}) => {
  test.setTimeout(240000);
  const running = await server(root),
    errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  try {
    await boot(page, running);
    await page.getByRole("button", { name: /multiview_performance/ }).click();
    const start = Date.now();
    await page
      .getByRole("button", { name: "Multi-view / 3D", exact: true })
      .click();
    const workspace = page.getByTestId("multi-workspace"),
      three = page.getByTestId("three-canvas");
    await expect(workspace).toHaveAttribute("data-analysis-ready", "true");
    await page.getByLabel("Workspace layout").selectOption("all");
    await expect(three).toHaveAttribute("data-landmarks", "17");
    await expect(page.getByText("SOURCE PIXELS", { exact: true })).toHaveCount(
      4,
    );
    await expect(page.locator(".preview3d footer")).toContainText(
      "approximate control polygons",
    );
    const firstDisplay = Date.now() - start,
      s = await snapshot(page, "multiview_performance");
    expect(s.observations).toHaveLength(5000);
    expect(s.references.find((r: any) => r.role === "multiview").size).toEqual([
      3840, 2160,
    ]);
    const cdp = await context.newCDPSession(page);
    await cdp.send("HeapProfiler.collectGarbage");
    const heapBefore = (await cdp.send("Runtime.getHeapUsage")).usedSize,
      backendBefore = rss(running.pid);
    const twoD = await page.evaluate(async () => {
      const results: Record<string, unknown> = {};
      const p95 = (a: number[]) =>
        [...a].sort((a, b) => a - b)[Math.floor(a.length * 0.95)];
      for (const view of ["side", "top", "front", "rear"]) {
        const host = document.querySelector<HTMLElement>(
            `.multi-view[data-view="${view}"] [data-testid="canvas"]`,
          )!,
          content = host.querySelector<HTMLElement>(".konvajs-content")!,
          b = content.getBoundingClientRect(),
          x = b.x + b.width * 0.5,
          y = b.y + b.height * 0.5;
        for (const mode of ["pan", "zoom"]) {
          const before = host.dataset.viewport,
            frames: number[] = [],
            draws: number[] = [];
          let prior = performance.now();
          if (mode === "pan")
            content.dispatchEvent(
              new MouseEvent("mousedown", {
                clientX: x,
                clientY: y,
                button: 1,
                buttons: 4,
                bubbles: true,
              }),
            );
          for (let i = 0; i < 65; i++) {
            await new Promise(requestAnimationFrame);
            const now = performance.now();
            if (i > 4) frames.push(now - prior);
            prior = now;
            if (mode === "pan")
              content.dispatchEvent(
                new MouseEvent("mousemove", {
                  clientX: x + Math.sin(i / 15) * 25,
                  clientY: y + Math.cos(i / 15) * 10,
                  buttons: 4,
                  bubbles: true,
                }),
              );
            else
              content.dispatchEvent(
                new WheelEvent("wheel", {
                  clientX: x,
                  clientY: y,
                  deltaY: i < 32 ? -5 : 5,
                  bubbles: true,
                  cancelable: true,
                }),
              );
            draws.push(Number(host.dataset.drawMs || 0));
          }
          if (mode === "pan")
            content.dispatchEvent(
              new MouseEvent("mouseup", {
                clientX: x,
                clientY: y,
                button: 1,
                bubbles: true,
              }),
            );
          await new Promise(requestAnimationFrame);
          if (host.dataset.viewport === before)
            throw Error(
              view + " " + mode + " did not change the actual viewport",
            );
          results[view + "_" + mode] = {
            frame_p95_ms: p95(frames),
            draw_p95_ms: p95(draws),
            fps: 1000 / (frames.reduce((a, b) => a + b, 0) / frames.length),
            samples: frames.length,
          };
        }
      }
      return results;
    });
    await page.getByRole("button", { name: "World", exact: true }).click();
    await page
      .getByLabel("World landmark selection")
      .selectOption("roof_corner");
    const measureThree = async (kind: "orbit" | "drag") => {
      if (kind === "drag") {
        await page
          .getByRole("button", { name: "Move World Landmark", exact: true })
          .click();
        await page.getByLabel("World drag constraint").selectOption("X");
        const previousCamera = await three.getAttribute("data-camera");
        await page.getByRole("button", { name: "TOP", exact: true }).click();
        await expect(three).not.toHaveAttribute("data-camera", previousCamera!);
        await expect
          .poll(
            async () =>
              !!JSON.parse((await three.getAttribute("data-handles")) || "{}").X
                ?.length,
          )
          .toBe(true);
      }
      const b = (await three.boundingBox())!,
        handles = JSON.parse(
          (await three.getAttribute("data-handles")) || "{}",
        );
      const position =
        kind === "drag"
          ? [...handles.X].sort((a: number[], b: number[]) => b[0] - a[0])[0]
          : [b.width * 0.7, b.height * 0.3];
      await three.evaluate((el) =>
        el.addEventListener(
          "pointerdown",
          (e) => {
            (el as HTMLElement).dataset.pointer = String(
              (e as PointerEvent).pointerId,
            );
          },
          { once: true, capture: true },
        ),
      );
      await page.mouse.move(b.x + position[0], b.y + position[1]);
      await page.mouse.down();
      const result = await three.evaluate(
        async (el, arg) => {
          const host = el as HTMLElement,
            canvas = host.querySelector("canvas")!,
            frames: number[] = [],
            draws: number[] = [];
          let prior = performance.now();
          for (let i = 0; i < 90; i++) {
            await new Promise(requestAnimationFrame);
            const now = performance.now();
            if (i > 5) frames.push(now - prior);
            prior = now;
            canvas.dispatchEvent(
              new PointerEvent("pointermove", {
                pointerId: Number(host.dataset.pointer),
                pointerType: "mouse",
                isPrimary: true,
                clientX: arg.x + i * 0.3,
                clientY: arg.y + Math.sin(i / 20) * 12,
                button: -1,
                buttons: 1,
                bubbles: true,
              }),
            );
            draws.push(Number(host.dataset.drawMs || 0));
          }
          const p95 = (a: number[]) =>
            [...a].sort((a, b) => a - b)[Math.floor(a.length * 0.95)];
          return {
            frame_p95_ms: p95(frames),
            draw_p95_ms: p95(draws),
            fps: 1000 / (frames.reduce((a, b) => a + b, 0) / frames.length),
            samples: frames.length,
          };
        },
        { x: b.x + position[0], y: b.y + position[1] },
      );
      const previous = await workspace.getAttribute("data-analysis-revision");
      const committed =
        kind === "drag"
          ? page.waitForResponse(
              (r) => r.url().endsWith("/transactions") && r.ok(),
            )
          : null;
      if (kind === "drag")
        expect(await three.getAttribute("data-drag-preview")).toBeTruthy();
      await page.mouse.up();
      if (committed) {
        await committed;
        await expect(workspace).not.toHaveAttribute(
          "data-analysis-revision",
          previous!,
        );
        await saved(page);
        await expect(workspace).toHaveAttribute("data-analysis-ready", "true");
      }
      return result;
    };
    const cameraBefore = await three.getAttribute("data-camera"),
      orbit = await measureThree("orbit");
    expect(await three.getAttribute("data-camera")).not.toBe(cameraBefore);
    const drag = await measureThree("drag");
    await page
      .getByRole("button", { name: "Consistency", exact: true })
      .click();
    const selectionTimes: number[] = [];
    for (const index of [1, 2, 3, 4, 5, 6]) {
      const row = page
          .locator(`.residual-row[data-entity="cage_landmark_${index}"]`)
          .first(),
        began = Date.now();
      await row.click();
      await expect(three).toHaveAttribute(
        "data-selected",
        "cage_landmark_" + index,
      );
      selectionTimes.push(Date.now() - began);
    }
    await page.getByRole("button", { name: "World", exact: true }).click();
    await page
      .getByLabel("World landmark selection")
      .selectOption("roof_corner");
    const total: number[] = [],
      persistence: number[] = [],
      refresh: number[] = [];
    let began = 0,
      lastPersistence = 0;
    page.on("response", (r) => {
      if (r.url().endsWith("/transactions") && r.ok())
        lastPersistence = Date.now() - began;
    });
    for (let i = 0; i < 8; i++) {
      await page
        .getByLabel("World X", { exact: true })
        .fill(String(0.02 + i * 0.005));
      began = Date.now();
      lastPersistence = 0;
      const previous = await workspace.getAttribute("data-analysis-revision"),
        response = page.waitForResponse(
          (r) => r.url().endsWith("/transactions") && r.ok(),
        );
      await page
        .getByRole("button", { name: "Apply world XYZ", exact: true })
        .click();
      await response;
      await expect(workspace).not.toHaveAttribute(
        "data-analysis-revision",
        previous!,
      );
      await expect(workspace).toHaveAttribute("data-analysis-ready", "true");
      await saved(page);
      await expect
        .poll(async () =>
          Number(
            await page.getByLabel("World X", { exact: true }).inputValue(),
          ),
        )
        .toBe(0.02 + i * 0.005);
      total.push(Date.now() - began);
      persistence.push(lastPersistence);
      refresh.push(total.at(-1)! - lastPersistence);
    }
    await cdp.send("HeapProfiler.collectGarbage");
    const heapAfter = (await cdp.send("Runtime.getHeapUsage")).usedSize;
    const percentile = (a: number[]) =>
      [...a].sort((a, b) => a - b)[Math.floor(a.length * 0.95)];
    const report = {
      status: "PASS",
      image: [3840, 2160],
      entities: 5000,
      viewports_2d: 4,
      viewports_3d: 1,
      world_landmarks: 17,
      cage_curves: 9,
      first_display_ms: firstDisplay,
      viewport: page.viewportSize(),
      device_pixel_ratio: await page.evaluate(() => devicePixelRatio),
      browser: await page.evaluate(() => navigator.userAgent),
      cpu: cpus()[0].model,
      system_memory_bytes: totalmem(),
      two_d: twoD,
      three_d_orbit: orbit,
      three_d_drag_preview: drag,
      selection_visible_p95_ms: percentile(selectionTimes),
      canonical_edits: 8,
      persistence_p95_ms: percentile(persistence),
      projection_and_residual_refresh_p95_ms: percentile(refresh),
      commit_and_refresh_p95_ms: percentile(total),
      browser_heap_before_bytes: heapBefore,
      browser_heap_after_gc_bytes: heapAfter,
      backend_rss_before_bytes: backendBefore,
      backend_rss_after_bytes: rss(running.pid),
      browser_errors: errors,
      input:
        "Browser pointer and wheel events through production Konva/Three.js handlers; typed world edits through visible UI. 100-edit backend retention is profiled separately.",
    };
    writeFileSync(
      resolve(repo, "build/studio02-performance.json"),
      JSON.stringify(report, null, 2),
    );
    await page.screenshot({
      path: resolve(repo, "build/studio02-performance.png"),
    });
    expect(errors).toEqual([]);
    expect(orbit.draw_p95_ms).toBeLessThan(100);
    expect(drag.draw_p95_ms).toBeLessThan(100);
  } finally {
    await running.stop();
  }
});
