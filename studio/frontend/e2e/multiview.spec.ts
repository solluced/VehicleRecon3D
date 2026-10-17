import { test, expect } from "@playwright/test";
import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync, appendFileSync } from "node:fs";
import { resolve } from "node:path";
import { repo, python, server, boot, saved, snapshot } from "./harness";
const root = resolve(
  repo,
  "build/studio02-multiview-" + Date.now(),
  "projects",
);
const gizmoRoot = root + "_gizmo";
test.beforeAll(() => {
  for (const target of [root, gizmoRoot]) {
    const r = spawnSync(
      python,
      [
        resolve(repo, "studio/backend/tests/prepare_multiview.py"),
        target,
        ...(target === root ? ["--legacy"] : []),
      ],
      { cwd: repo, encoding: "utf8", windowsHide: true },
    );
    if (r.status !== 0) throw Error(r.stderr);
  }
});
async function current(page: any) {
  return snapshot(page, "consistent_fixture");
}
async function evidence(page: any) {
  return page.evaluate(async () => {
    const projects = await (await fetch("/api/v1/projects")).json();
    const p = projects.find(
      (p: any) => p.project?.asset_name === "consistent_fixture",
    );
    return (await fetch("/api/v1/projects/" + p.id + "/analysis")).json();
  });
}
async function ready(page: any) {
  await expect(page.getByTestId("multi-workspace")).toHaveAttribute(
    "data-analysis-ready",
    "true",
  );
  await saved(page);
}
async function openStudy(page: any, running: any) {
  await boot(page, running);
  await page.getByRole("button", { name: /consistent_fixture/ }).click();
  await page
    .getByRole("button", { name: "Multi-view / 3D", exact: true })
    .click();
  await ready(page);
  await expect(page.getByText("SOURCE PIXELS", { exact: true })).toHaveCount(4);
}
async function sourcePosition(page: any, view: string, pixel: number[]) {
  const cell = page.locator(`.multi-view[data-view="${view}"]`),
    canvas = cell.getByTestId("canvas");
  const box = (await canvas.boundingBox())!,
    camera = JSON.parse((await canvas.getAttribute("data-viewport"))!);
  return {
    x: box.x + camera.x + pixel[0] * camera.scale,
    y: box.y + camera.y + pixel[1] * camera.scale,
  };
}
test("multi-view binding, distinct moves, fit proposal, 3D selection, reviews and roundtrip", async ({
  page,
}) => {
  let running = await server(root);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  try {
    await openStudy(page, running);
    let a = await evidence(page);
    expect(a.residuals.status).toBe("PASS");
    expect(a.coverage[0].views).toEqual({ front: 1, side: 1, rear: 1, top: 1 });
    await page
      .getByRole("button", { name: "Correspondence", exact: true })
      .click();
    let p = await sourcePosition(page, "side", [128, 78]);
    await page.mouse.click(p.x, p.y);
    await expect(
      page.getByText("SOURCE: obs_roof_side", { exact: false }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Unbind selected observation", exact: true })
      .click();
    await ready(page);
    expect((await evidence(page)).correspondences).toHaveLength(3);
    await page
      .getByRole("button", { name: "Bind observation to world", exact: true })
      .click();
    await ready(page);
    expect((await evidence(page)).correspondences).toHaveLength(4);
    const before = await current(page),
      worldBefore = (await evidence(page)).world_landmarks;
    p = await sourcePosition(page, "side", [128, 78]);
    await page.mouse.move(p.x, p.y);
    await page.mouse.down();
    await page.mouse.move(p.x + 24, p.y + 7, { steps: 8 });
    await page.mouse.up();
    await ready(page);
    await expect
      .poll(async () =>
        JSON.stringify((await current(page)).observations[0].pixel),
      )
      .not.toBe(JSON.stringify(before.observations[0].pixel));
    expect((await evidence(page)).world_landmarks).toEqual(worldBefore);
    await page
      .getByRole("button", { name: "Consistency", exact: true })
      .click();
    await expect(page.locator(".residual-row.fail").first()).toBeVisible();
    await page
      .getByRole("button", { name: "Multi-view Undo", exact: true })
      .click();
    await ready(page);
    await page.getByLabel("Workspace layout").selectOption("all");
    const three = page.getByTestId("three-canvas");
    await expect(three).toHaveAttribute("data-landmarks", "1");
    const screen = JSON.parse(
        (await three.getAttribute("data-points"))!,
      ).roof_corner,
      box = (await three.boundingBox())!;
    await page.mouse.click(box.x + screen[0], box.y + screen[1]);
    await expect(three).toHaveAttribute("data-selected", "roof_corner");
    await page
      .getByRole("button", { name: "Move World Landmark", exact: true })
      .click();
    await page.getByRole("button", { name: "World", exact: true }).click();
    await page.getByLabel("World X", { exact: true }).fill("0.1");
    await page.getByLabel("World Y", { exact: true }).fill("0.6");
    await page.getByLabel("World Z", { exact: true }).fill("1.1");
    const projections = (await evidence(page)).residuals.rows.map(
      (r: any) => r.projected_pixel,
    );
    await page
      .getByRole("button", { name: "Apply world XYZ", exact: true })
      .click();
    await ready(page);
    a = await evidence(page);
    expect(a.world_landmarks.roof_corner).toEqual([0.1, 0.6, 1.1]);
    expect(
      a.residuals.rows.every(
        (r: any, i: number) =>
          JSON.stringify(r.projected_pixel) !== JSON.stringify(projections[i]),
      ),
    ).toBe(true);
    const revision = (await current(page)).revision;
    await page
      .getByRole("button", { name: "Solve from observations", exact: true })
      .click();
    await expect(
      page.getByRole("region", { name: "Fit proposal" }),
    ).toBeVisible();
    expect((await current(page)).revision).toBe(revision);
    await expect(three).not.toHaveAttribute("data-proposal", "");
    await page
      .getByRole("button", { name: "APPLY proposal", exact: true })
      .click();
    await ready(page);
    a = await evidence(page);
    expect(a.world_landmarks.roof_corner[0]).toBeCloseTo(0, 8);
    expect(a.world_landmarks.roof_corner[1]).toBeCloseTo(0.5, 8);
    await page
      .getByRole("button", { name: "Multi-view Undo", exact: true })
      .click();
    await ready(page);
    expect((await evidence(page)).world_landmarks.roof_corner).toEqual([
      0.1, 0.6, 1.1,
    ]);
    await page
      .getByRole("button", { name: "Multi-view Redo", exact: true })
      .click();
    await ready(page);
    expect((await evidence(page)).residuals.status).toBe("PASS");
    await page.getByRole("button", { name: "Review", exact: true }).click();
    await page
      .getByLabel("Reviewer", { exact: true })
      .fill("Browser fixture reviewer");
    await page
      .getByLabel("Review note", { exact: true })
      .fill("Inspected four individual residuals and current input identity.");
    await page.getByLabel("Review decision").selectOption("ACCEPTED");
    await page.getByRole("button", { name: "Record source decision" }).click();
    await ready(page);
    expect((await evidence(page)).reviews.source.status.state).toBe("READY");
    await page.getByLabel("Review type").selectOption("cage");
    await page.getByLabel("Review decision").selectOption("ACCEPTED");
    await page.getByRole("button", { name: "Record cage decision" }).click();
    await ready(page);
    expect((await evidence(page)).reviews.cage.status.state).toBe("READY");
    await page.getByLabel("Review type").selectOption("source");
    await page
      .getByLabel("Review decision")
      .selectOption("INCONSISTENT_SOURCE");
    await page
      .getByLabel("Review note")
      .fill("Explicit rejection scenario; do not build surfaces.");
    await page.getByRole("button", { name: "Record source decision" }).click();
    await ready(page);
    expect((await current(page)).readiness.surfaces.state).toBe("BLOCKED");
    expect((await evidence(page)).reviews.source.status.decision).toBe(
      "INCONSISTENT_SOURCE",
    );
    const final = await current(page),
      finalEvidence = await evidence(page);
    await page.screenshot({
      path: resolve(repo, "build/studio02-multiview.png"),
    });
    await page.reload();
    await page.getByRole("button", { name: /consistent_fixture/ }).click();
    expect((await current(page)).revision).toBe(final.revision);
    await running.stop();
    running = await server(root);
    await openStudy(page, running);
    expect((await current(page)).observations).toEqual(final.observations);
    expect((await evidence(page)).world_landmarks).toEqual(
      finalEvidence.world_landmarks,
    );
    expect((await current(page)).revision).toBe(final.revision);
    await page.getByRole("button", { name: "World", exact: true }).click();
    await page
      .getByLabel("World landmark selection")
      .selectOption("roof_corner");
    await page.getByRole("button", { name: "Solve from observations" }).click();
    await expect(
      page.getByRole("region", { name: "Fit proposal" }),
    ).toBeVisible();
    appendFileSync(resolve(root, "study/generated/cage.json"), "\n");
    await expect(page.locator(".save-state")).toHaveText("Conflict");
    await expect(
      page.getByRole("region", { name: "Fit proposal" }),
    ).toHaveCount(0);
    expect(errors).toEqual([]);
    writeFileSync(
      resolve(repo, "build/studio02-roundtrip.json"),
      JSON.stringify(
        {
          status: "PASS",
          revision: final.revision,
          stable_ids: final.observations.map((o: any) => o.id),
          world_landmarks: finalEvidence.world_landmarks,
          source_review: "INCONSISTENT_SOURCE",
          source_cage_acceptance: true,
          refresh: true,
          restart: true,
          external_world_conflict: true,
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

test("known Mark II conflict is visible without editing canonical data", async ({
  page,
}) => {
  const running = await server(root);
  try {
    await boot(page, running);
    await page.getByRole("button", { name: /mark.*ii|mark2/i }).click();
    await page
      .getByRole("button", { name: "Multi-view / 3D", exact: true })
      .click();
    await ready(page);
    await expect(
      page.locator('.multi-view[data-view="side"]>header'),
    ).toContainText("multiview");
    await expect(page.locator(".source-condition")).toContainText(
      "INCONSISTENT_SOURCE",
    );
    await expect(page.locator(".residual-row.fail").first()).toBeVisible();
    await page
      .getByRole("button", { name: "Diagnostics", exact: true })
      .click();
    await expect(
      page.getByText("CANDIDATE REJECTED / NOT ACTIVE", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("table", { name: "Longitudinal ratios" }),
    ).toContainText("a_pillar_roof");
    await page.screenshot({
      path: resolve(repo, "build/studio02-mark2-readonly.png"),
    });
    await expect(
      page.getByRole("button", { name: "Multi-view Undo" }),
    ).toBeDisabled();
  } finally {
    await running.stop();
  }
});

test("native Three.js X and XZ gizmos preview locally and commit once at release", async ({
  page,
}) => {
  const running = await server(gizmoRoot);
  try {
    await openStudy(page, running);
    await page.getByLabel("Workspace layout").selectOption("split");
    await page.getByRole("button", { name: "World", exact: true }).click();
    await page
      .getByLabel("World landmark selection")
      .selectOption("roof_corner");
    await page
      .getByRole("button", { name: "Move World Landmark", exact: true })
      .click();
    const three = page.getByTestId("three-canvas"),
      requests: string[] = [];
    page.on("request", (r) => {
      if (r.url().endsWith("/transactions")) requests.push(r.postData() || "");
    });
    await expect(three).toHaveAttribute("data-camera", /^\[/);
    for (const mode of ["X", "XZ"]) {
      await page.getByLabel("World drag constraint").selectOption(mode);
      const previousCamera = await three.getAttribute("data-camera");
      await page
        .getByRole("button", {
          name: mode === "X" ? "TOP" : "LEFT",
          exact: true,
        })
        .click();
      // Handle screen coordinates belong to the last rendered camera. On a
      // software renderer the preset click can precede that frame by >1 event.
      await expect(three).not.toHaveAttribute("data-camera", previousCamera!);
      await expect
        .poll(
          async () =>
            !!JSON.parse((await three.getAttribute("data-handles")) || "{}")[
              mode
            ]?.length,
        )
        .toBe(true);
      const candidates = JSON.parse(
          (await three.getAttribute("data-handles"))!,
        )[mode] as number[][],
        handle = [...candidates].sort((a, b) => b[0] - a[0])[0],
        box = (await three.boundingBox())!,
        before = await evidence(page),
        count = requests.length;
      const previousPreview = await three.getAttribute("data-drag-preview");
      await page.mouse.move(box.x + handle[0], box.y + handle[1]);
      await page.mouse.down();
      await page.mouse.move(
        box.x + handle[0] + 35,
        box.y + handle[1] - (mode === "XZ" ? 18 : 0),
        { steps: 12 },
      );
      await expect(three).not.toHaveAttribute(
        "data-drag-preview",
        previousPreview || "",
      );
      expect(await three.getAttribute("data-drag-preview")).toBeTruthy();
      expect(requests.length).toBe(count);
      expect((await evidence(page)).world_landmarks).toEqual(
        before.world_landmarks,
      );
      await page.mouse.up();
      await expect.poll(() => requests.length).toBe(count + 1);
      await ready(page);
      const after = (await evidence(page)).world_landmarks.roof_corner;
      expect(after[0]).not.toBe(before.world_landmarks.roof_corner[0]);
      expect(after[1]).toBe(before.world_landmarks.roof_corner[1]);
      if (mode === "X")
        expect(after[2]).toBe(before.world_landmarks.roof_corner[2]);
      else expect(after[2]).not.toBe(before.world_landmarks.roof_corner[2]);
      expect(JSON.parse(requests.at(-1)!).commands[0].type).toBe(
        "MoveWorldLandmark",
      );
    }
    await page.screenshot({ path: resolve(repo, "build/studio02-gizmo.png") });
  } finally {
    await running.stop();
  }
});
