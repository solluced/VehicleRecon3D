import { test, expect } from "@playwright/test";
import { resolve } from "node:path";
import { readFileSync, writeFileSync, appendFileSync } from "node:fs";
import { createHash } from "node:crypto";
import {
  repo,
  prepare,
  server,
  boot,
  snapshot,
  camera,
  saved,
} from "./harness";
const root = resolve(
  repo,
  "build/studio-v01b-browser-" + Date.now(),
  "projects",
);
test.beforeAll(() => prepare(root));
test("manual authoring survives refresh and backend restart, with conflicts fenced", async ({
  page,
}) => {
  let running = await server(root);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  try {
    await boot(page, running);
    await page.getByLabel("Project name", { exact: true }).fill("Manual_Study");
    await page.getByRole("button", { name: "Create project →" }).click();
    await page
      .getByLabel("Import reference", { exact: true })
      .first()
      .setInputFiles(resolve(root, "../reference4k.png"));
    await page.getByText("SOURCE PIXELS", { exact: true }).waitFor();
    await expect
      .poll(async () => !!(await snapshot(page)).preferences.viewport)
      .toBe(true);
    await saved(page);
    const canvas = page.getByTestId("canvas"),
      box = (await canvas.boundingBox())!;
    const screen = async (x: number, y: number) => {
      const v = await camera(page),
        b = (await canvas.boundingBox())!;
      return { x: b.x + v.x + x * v.scale, y: b.y + v.y + y * v.scale };
    };
    const before = await camera(page),
      pointer = {
        x: Math.round(box.width * 0.6),
        y: Math.round(box.height * 0.55),
      };
    await page.mouse.move(box.x + pointer.x, box.y + pointer.y);
    await page.mouse.wheel(0, -200);
    await expect
      .poll(async () => (await camera(page)).scale)
      .toBeGreaterThan(before.scale);
    const after = await camera(page);
    expect((pointer.x - after.x) / after.scale).toBeCloseTo(
      (pointer.x - before.x) / before.scale,
      6,
    );
    expect((pointer.y - after.y) / after.scale).toBeCloseTo(
      (pointer.y - before.y) / before.scale,
      6,
    );
    const panBefore = await camera(page);
    await page.keyboard.down("Space");
    await page.mouse.down();
    await page.mouse.move(box.x + pointer.x + 70, box.y + pointer.y + 30, {
      steps: 8,
    });
    await page.mouse.up();
    await page.keyboard.up("Space");
    expect((await camera(page)).x - panBefore.x).toBeCloseTo(70, 0);
    await page.getByRole("button", { name: "Fit", exact: true }).click();
    await expect
      .poll(async () => {
        const s = await snapshot(page),
          v = await camera(page);
        return Math.abs((s.preferences.viewport?.scale || 0) - v.scale) < 1e-6;
      })
      .toBe(true);
    await saved(page);
    await page.getByRole("button", { name: "+ Point", exact: true }).click();
    let p = await screen(1000, 800);
    await page.mouse.click(p.x, p.y);
    await expect
      .poll(async () => (await snapshot(page)).observations.length)
      .toBe(1);
    await saved(page);
    p = await screen(2500, 1200);
    await page.mouse.click(p.x, p.y);
    await expect
      .poll(async () => (await snapshot(page)).observations.length)
      .toBe(2);
    await saved(page);
    let s = await snapshot(page),
      point = s.observations[0];
    const old = point.pixel;
    // Delete a real, independently created point through the visible editor.
    p = await screen(1800, 1500);
    await page.mouse.click(p.x, p.y);
    await expect
      .poll(async () => (await snapshot(page)).observations.length)
      .toBe(3);
    await saved(page);
    await page.getByRole("button", { name: "↖ Select", exact: true }).click();
    const temporary = (await snapshot(page)).observations.at(-1);
    p = await screen(temporary.pixel[0], temporary.pixel[1]);
    await page.mouse.click(p.x, p.y);
    await expect(
      page.getByRole("button", { name: "Delete entity", exact: true }),
    ).toBeEnabled();
    await page.keyboard.press("Delete");
    await expect
      .poll(async () => (await snapshot(page)).observations.length)
      .toBe(2);
    await saved(page);
    await page.getByRole("button", { name: "↖ Select", exact: true }).click();
    p = await screen(old[0], old[1]);
    const commits: string[] = [];
    page.on("request", (r) => {
      if (r.url().endsWith("/transactions")) commits.push(r.postData() || "");
    });
    const count = commits.length;
    await page.mouse.move(p.x, p.y);
    await page.mouse.down();
    await page.mouse.move(p.x + 24, p.y + 12, { steps: 12 });
    await page.mouse.up();
    await expect
      .poll(async () => (await snapshot(page)).observations[0].pixel[0])
      .not.toBe(old[0]);
    await saved(page);
    expect(commits.length - count).toBe(1);
    expect(JSON.parse(commits.at(-1)!).commands[0].type).toBe(
      "MoveObservation",
    );
    await page.getByLabel("Find semantic role").fill("hood");
    await page
      .getByLabel("Semantic role", { exact: true })
      .selectOption("hood");
    await page.getByRole("button", { name: "Apply properties" }).click();
    await expect
      .poll(async () => (await snapshot(page)).observations[0].semantic_role)
      .toBe("hood");
    await saved(page);
    await page.keyboard.press("Control+z");
    await expect
      .poll(async () => (await snapshot(page)).observations[0].semantic_role)
      .toBe("roof");
    await saved(page);
    await page.getByRole("button", { name: "Redo", exact: true }).click();
    await expect
      .poll(async () => (await snapshot(page)).observations[0].semantic_role)
      .toBe("hood");
    await saved(page);
    for (const kind of ["Polyline", "Spline"]) {
      await page.getByRole("button", { name: new RegExp(kind + "$") }).click();
      for (const [x, y] of [
        [600, 500],
        [1500, 400],
        [2200, 650],
      ]) {
        p = await screen(x, y);
        await page.mouse.click(p.x, p.y);
      }
      await page.getByRole("button", { name: "Finish curve" }).click();
      await expect
        .poll(
          async () =>
            (await snapshot(page)).observations.filter(
              (o: any) => o.kind === kind.toLowerCase(),
            ).length,
        )
        .toBe(1);
      await saved(page);
    }
    s = await snapshot(page);
    const spline = s.observations.find((o: any) => o.kind === "spline");
    await page.getByRole("button", { name: "+ Knot", exact: true }).click();
    p = await screen(2800, 900);
    await page.mouse.click(p.x, p.y);
    await expect
      .poll(
        async () =>
          (await snapshot(page)).observations.find(
            (o: any) => o.id === spline.id,
          ).points.length,
      )
      .toBe(4);
    await saved(page);
    await page.getByRole("button", { name: "↖ Select", exact: true }).click();
    p = await screen(2800, 900);
    await page.mouse.click(p.x, p.y);
    await page.keyboard.press("Delete");
    await expect
      .poll(
        async () =>
          (await snapshot(page)).observations.find(
            (o: any) => o.id === spline.id,
          ).points.length,
      )
      .toBe(3);
    await saved(page);
    await page.getByRole("button", { name: "Settings", exact: true }).click();
    await page
      .getByLabel("Asset name", { exact: true })
      .fill("Manual_Study_Renamed");
    await page.getByLabel("length (m)", { exact: true }).fill("4.8");
    await page
      .getByLabel("Dimension provenance", { exact: true })
      .selectOption("measured");
    await page
      .getByLabel("Dimension citation", { exact: true })
      .fill("Analytical roundtrip fixture; not a vehicle measurement");
    await page.getByRole("button", { name: "Apply settings" }).click();
    await expect
      .poll(
        async () =>
          (await snapshot(page, "Manual_Study_Renamed")).project.dimensions
            .length_m,
      )
      .toBe(4.8);
    await saved(page);
    const final = await snapshot(page, "Manual_Study_Renamed");
    await page.screenshot({
      path: resolve(repo, "build/studio-v01b-desktop.png"),
    });
    await page.reload();
    await page.getByRole("button", { name: /Manual_Study_Renamed/ }).click();
    await page.getByText("SOURCE PIXELS", { exact: true }).waitFor();
    let reopened = await snapshot(page, "Manual_Study_Renamed");
    expect(reopened.revision).toBe(final.revision);
    expect(reopened.observations).toEqual(final.observations);
    expect(reopened.project).toEqual(final.project);
    await running.stop();
    running = await server(root);
    await boot(page, running);
    await page.getByRole("button", { name: /Manual_Study_Renamed/ }).click();
    await page.getByText("SOURCE PIXELS", { exact: true }).waitFor();
    reopened = await snapshot(page, "Manual_Study_Renamed");
    expect(reopened.revision).toBe(final.revision);
    expect(reopened.observations).toEqual(final.observations);
    const raw = readFileSync(resolve(root, "../reference4k.png")),
      sha = createHash("sha256").update(raw).digest("hex");
    expect(reopened.references[0].sha256).toBe(sha);
    const active = JSON.parse(
      readFileSync(resolve(root, "manual_study/project.json"), "utf8"),
    );
    expect(
      readFileSync(
        resolve(root, "manual_study", active.references.multiview),
      ).equals(raw),
    ).toBe(true);
    // Replacing the tab's stream closes the previous owned connection. The
    // application's EventSource must reconnect with its native Last-Event-ID.
    await page.evaluate(
      () =>
        new Promise<void>((resolve, reject) => {
          const replacement = new EventSource(
            "/api/v1/events?tab_id=" + sessionStorage.getItem("vr-tab"),
          );
          replacement.addEventListener("resync", () => {
            replacement.close();
            resolve();
          });
          replacement.onerror = () => {
            replacement.close();
            reject(new Error("SSE replacement failed"));
          };
        }),
    );
    await expect(page.locator(".connection")).toHaveText("Reconnecting");
    await expect(page.locator(".connection")).toHaveText("Live", {
      timeout: 20000,
    });
    appendFileSync(resolve(root, "manual_study/project.json"), "\n");
    await expect(page.locator(".save-state")).toHaveText("Conflict");
    const externalBytes = readFileSync(
      resolve(root, "manual_study/project.json"),
    );
    await page
      .getByRole("button", { name: "Reload canonical state", exact: true })
      .click();
    await saved(page);
    expect(
      readFileSync(resolve(root, "manual_study/project.json")).equals(
        externalBytes,
      ),
    ).toBe(true);
    expect(errors).toEqual([]);
    writeFileSync(
      resolve(repo, "build/studio-v01b-roundtrip.json"),
      JSON.stringify(
        {
          status: "PASS",
          image: [3840, 2160],
          points: final.observations.filter((o: any) => o.kind === "point")
            .length,
          curves: final.observations.filter((o: any) => o.points).length,
          stable_entities: final.observations.map((o: any) => o.id),
          revision: final.revision,
          source_sha256: sha,
          refresh: true,
          backend_restart: true,
          external_conflict: true,
          drag_commands: 1,
          browser_errors: errors,
        },
        null,
        2,
      ),
    );
  } finally {
    await running.stop();
  }
});

test("laptop canvas, high-DPI 1:1 and stale review state", async ({
  browser,
}) => {
  const context = await browser.newContext({
      viewport: { width: 1100, height: 760 },
      deviceScaleFactor: 2,
    }),
    page = await context.newPage();
  const running = await server(root);
  try {
    await page.setViewportSize({ width: 1100, height: 760 });
    await boot(page, running);
    await page
      .getByRole("button", { name: /consistent_fixture/ })
      .first()
      .click();
    await page.getByText("SOURCE PIXELS", { exact: true }).waitFor();
    await page.getByRole("button", { name: "1:1", exact: true }).click();
    await expect
      .poll(async () =>
        Math.abs(
          (await camera(page)).scale *
            (await page.evaluate(() => devicePixelRatio)) -
            1,
        ),
      )
      .toBeLessThan(0.001);
    await page.getByRole("button", { name: "Fit", exact: true }).click();
    const snap = await snapshot(page, "consistent_fixture");
    const canvas = page.getByTestId("canvas"),
      box = (await canvas.boundingBox())!,
      v = await camera(page);
    expect(box.width).toBeGreaterThan(300);
    expect(box.height).toBeGreaterThan(200);
    const o = snap.observations.find((o: any) => o.view === "side");
    await expect
      .poll(
        async () =>
          !!(await snapshot(page, "consistent_fixture")).preferences.viewport,
      )
      .toBe(true);
    await saved(page);
    await page.mouse.click(
      box.x + v.x + o.pixel[0] * v.scale,
      box.y + v.y + o.pixel[1] * v.scale,
    );
    await page
      .getByLabel("Pixel X", { exact: true })
      .fill(String(o.pixel[0] + 1));
    await page.getByRole("button", { name: "Apply properties" }).click();
    await expect
      .poll(
        async () =>
          (await snapshot(page, "consistent_fixture")).readiness.source_review
            .current,
      )
      .toBe(false);
    await page
      .locator(".readiness-grid summary")
      .filter({ hasText: /^source review/ })
      .click();
    await expect(page.locator(".readiness-grid")).toContainText("stale");
    await page.screenshot({
      path: resolve(repo, "build/studio-v01b-laptop.png"),
    });
  } finally {
    await context.close();
    await running.stop();
  }
});
