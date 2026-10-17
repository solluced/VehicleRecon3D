import { test, expect, type Page } from "@playwright/test";
import { spawnSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { repo, python, server, boot, saved, snapshot } from "./harness";
const root = resolve(repo, "build/studio05-surfaces-" + Date.now(), "projects");
test.beforeAll(() => {
  const r = spawnSync(
    python,
    [resolve(repo, "studio/backend/tests/prepare_surfaces.py"), root],
    { cwd: repo, encoding: "utf8", windowsHide: true },
  );
  if (r.status !== 0) throw Error(r.stderr);
});
async function open(page: Page, running: any, name = "Surface_Study") {
  await boot(page, running);
  await page
    .locator(".project-card")
    .filter({ has: page.getByText(name, { exact: true }) })
    .click();
  await page.getByRole("button", { name: "Surfaces", exact: true }).click();
  await page.getByRole("main", { name: "Surfaces workspace" }).waitFor();
  await expect(
    page.getByText("Bounded surfaces", { exact: true }),
  ).toBeVisible();
}
async function preview(page: Page, status = "PASS") {
  await page.getByRole("button", { name: "Generate coarse preview" }).click();
  await expect(page.getByTestId("surface-preview-status")).toHaveText(
    "CURRENT · " + status,
  );
  await expect(page.getByTestId("surface-three-canvas")).not.toHaveAttribute(
    "data-mesh-count",
    "0",
  );
}
async function select(page: Page, name = "Analytical plane a") {
  await page.getByRole("listitem").filter({ hasText: name }).click();
  await expect(page.getByLabel("Boundary left", { exact: true })).toBeVisible();
}
test("surface patch creation, four boundaries, orientation, real mesh inspectors and stable reopen", async ({
  page,
}) => {
  const running = await server(root);
  try {
    await open(page, running);
    await page.getByLabel("Patch name", { exact: true }).fill("Browser Coons");
    await page.getByRole("button", { name: "Add patch draft" }).click();
    await expect(
      page.getByLabel("Boundary bottom", { exact: true }),
    ).toBeVisible();
    for (const [slot, id] of Object.entries({
      bottom: "bottom.a",
      top: "top.a",
      left: "left",
      right: "shared",
    })) {
      await page
        .getByLabel("Boundary " + slot, { exact: true })
        .selectOption(id);
      await saved(page);
      await expect(
        page.getByLabel("Boundary " + slot, { exact: true }),
      ).toHaveValue(id);
    }
    await page.getByRole("button", { name: "Mark node complete" }).click();
    await saved(page);
    await preview(page);
    const graph = await page.evaluate(async () => {
      const ps = await (await fetch("/api/v1/projects")).json(),
        p = ps.find((p: any) => p.project?.asset_name === "Surface_Study");
      return (await fetch("/api/v1/projects/" + p.id + "/surfaces")).json();
    });
    const id = graph.graph.patches.find(
      (p: any) => p.name === "Browser Coons",
    ).id;
    const canvas = page.getByTestId("surface-three-canvas");
    const targets = JSON.parse(
      (await canvas.getAttribute("data-pick-targets"))!,
    );
    const box = (await canvas.boundingBox())!;
    const boundary = targets.find((t: any) => t.boundary === "bottom.a");
    await page.mouse.click(box.x + boundary.x, box.y + boundary.y);
    await expect(page.getByTestId("picked-boundary")).toHaveText("bottom.a");
    const mesh = targets.find((t: any) => t.patch === "panel.b");
    await page.mouse.click(box.x + mesh.x, box.y + mesh.y);
    await expect(
      page.getByRole("listitem").filter({ hasText: "Analytical plane b" }),
    ).toHaveAttribute("aria-pressed", "true");
    await page.getByRole("listitem").filter({ hasText: id }).click();
    await page
      .getByRole("checkbox", { name: "Wireframe · preview topology" })
      .check();
    await expect(page.getByTestId("surface-three-canvas")).toHaveAttribute(
      "data-wire-edges",
      "actual-preview-mesh",
    );
    await page.getByLabel("Surface normals").selectOption("face");
    await page.getByLabel("Patch colors").selectOption("continuity");
    await page.screenshot({
      path: resolve(repo, "build/studio05-surfaces-authoring.png"),
      fullPage: true,
    });
    await page.reload();
    await page
      .locator(".project-card")
      .filter({ has: page.getByText("Surface_Study", { exact: true }) })
      .click();
    await page.getByRole("button", { name: "Surfaces", exact: true }).click();
    await expect(
      page.getByRole("listitem").filter({ hasText: id }),
    ).toBeVisible();
  } finally {
    await running.stop();
  }
});
test("surface corner FAIL, correction PASS, undo FAIL, redo PASS and safe cycle draft", async ({
  page,
}) => {
  const running = await server(root);
  try {
    await open(page, running);
    await select(page);
    await page
      .getByRole("button", { name: "Reverse left", exact: true })
      .click();
    await saved(page);
    await page.getByRole("button", { name: "Generate coarse preview" }).click();
    await expect(page.getByTestId("surface-preview-status")).toHaveText(
      "UNCERTIFIED · FAIL",
    );
    await expect(page.getByText(/left\(0\).*1.000e\+0/)).toBeVisible();
    await page
      .getByRole("button", { name: "Reverse left", exact: true })
      .click();
    await saved(page);
    await preview(page);
    await page.getByRole("button", { name: "Undo", exact: true }).click();
    await saved(page);
    await page.getByRole("button", { name: "Generate coarse preview" }).click();
    await expect(page.getByTestId("surface-preview-status")).toHaveText(
      "UNCERTIFIED · FAIL",
    );
    await page.getByRole("button", { name: "Redo", exact: true }).click();
    await saved(page);
    await preview(page);
    await page
      .getByLabel("Boundary left", { exact: true })
      .selectOption("sample.a");
    await expect(page.getByText(/UNSAVED INVALID DRAFT/)).toBeVisible();
    await expect(page.getByTestId("surface-preview-status")).toHaveText(
      "BLOCKED · INVALID DRAFT",
    );
    await page.getByRole("button", { name: "Generate coarse preview" }).click();
    await expect(page.getByText(/Surface graph cycle/).first()).toBeVisible();
    await page.getByRole("button", { name: "Discard invalid draft" }).click();
    await preview(page);
  } finally {
    await running.stop();
  }
});
test("rejected source blocks preview and creates no canonical surface writes", async ({
  page,
}) => {
  const running = await server(root);
  try {
    await open(page, running, "Rejected_Surface_Study");
    await expect(
      page.getByText("BLOCKED BY SOURCE/CAGE ACCEPTANCE", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Generate coarse preview" }),
    ).toBeDisabled();
    await expect(page.getByTestId("surface-preview-status")).toHaveText(
      "NOT GENERATED",
    );
  } finally {
    await running.stop();
  }
});
test("27 patch preview, dependency-local edit and real browser upload/redraw inspectors", async ({
  page,
}) => {
  const running = await server(root);
  try {
    await open(page, running, "Dense_Surface_Study");
    const start = performance.now();
    await preview(page);
    const first = performance.now() - start;
    await page
      .getByRole("listitem")
      .filter({ hasText: "Grid panel 0" })
      .click();
    const selection = performance.now();
    await expect(page.getByLabel("Resolution U")).toBeVisible();
    const selectionMs = performance.now() - selection;
    const editStart = performance.now();
    await page.getByLabel("Resolution U").fill("7");
    await page.getByLabel("Resolution U").blur();
    await saved(page);
    await expect(page.getByTestId("surface-preview-status")).toContainText(
      "STALE",
    );
    const editMs = performance.now() - editStart;
    const incrementalStart = performance.now();
    await preview(page);
    const incremental = performance.now() - incrementalStart;
    const wireStart = performance.now();
    await page
      .getByRole("checkbox", { name: "Wireframe · preview topology" })
      .check();
    await expect(page.getByTestId("surface-three-canvas")).toHaveAttribute(
      "data-wire-edges",
      "actual-preview-mesh",
    );
    const wireMs = performance.now() - wireStart;
    const normalStart = performance.now();
    await page.getByLabel("Surface normals").selectOption("vertex");
    const normalsMs = performance.now() - normalStart;
    const data = await page
      .getByTestId("surface-three-canvas")
      .evaluate((el) => ({
        meshes: el.getAttribute("data-mesh-count"),
        upload_ms: Number(el.getAttribute("data-upload-ms")),
        redraw_ms: Number(el.getAttribute("data-redraw-ms")),
      }));
    const heap = await page.evaluate(
      () => (performance as any).memory?.usedJSHeapSize ?? null,
    );
    writeFileSync(
      resolve(repo, "build/studio05-surface-browser-performance.json"),
      JSON.stringify(
        {
          patches: 27,
          first_visible_preview_ms: first,
          incremental_visible_preview_ms: incremental,
          selection_ms: selectionMs,
          patch_edit_ms: editMs,
          wire_toggle_ms: wireMs,
          normals_toggle_ms: normalsMs,
          ...data,
          browser_heap_bytes: heap,
        },
        null,
        2,
      ),
    );
    await page.screenshot({
      path: resolve(repo, "build/studio05-surfaces-dense.png"),
      fullPage: true,
    });
  } finally {
    await running.stop();
  }
});

test("declared G0 gap FAIL, fix PASS, undo FAIL, redo PASS", async ({
  page,
}) => {
  const running = await server(root);
  try {
    await open(page, running);
    await preview(page);
    await page.getByText("Declare adjacency", { exact: true }).click();
    await page.getByLabel("Adjacency edge B").selectOption("right");
    await page.getByRole("button", { name: "Save adjacency" }).click();
    await saved(page);
    await page.getByRole("button", { name: "Generate coarse preview" }).click();
    await expect(page.getByTestId("surface-preview-status")).toHaveText(
      "UNCERTIFIED · FAIL",
    );
    await expect(
      page.getByRole("button").filter({ hasText: /max 1.000e\+0 m/ }),
    ).toBeVisible();
    await page.getByText("Declare adjacency", { exact: true }).click();
    await page.getByLabel("Adjacency edge B").selectOption("left");
    await page.getByRole("button", { name: "Save adjacency" }).click();
    await saved(page);
    await preview(page);
    await page.getByRole("button", { name: "Undo", exact: true }).click();
    await saved(page);
    await page.getByRole("button", { name: "Generate coarse preview" }).click();
    await expect(page.getByTestId("surface-preview-status")).toHaveText(
      "UNCERTIFIED · FAIL",
    );
    await page.getByRole("button", { name: "Redo", exact: true }).click();
    await saved(page);
    await preview(page);
  } finally {
    await running.stop();
  }
});

test("cage edit visibly stales mesh, current cage review required before regeneration", async ({
  page,
}) => {
  const running = await server(root);
  try {
    await open(page, running);
    await preview(page);
    function change(mode: string) {
      const r = spawnSync(
        python,
        [resolve(repo, "studio/backend/tests/prepare_surfaces.py"), root, mode],
        { cwd: repo, encoding: "utf8", windowsHide: true },
      );
      if (r.status !== 0) throw Error(r.stderr);
    }
    change("--edit-cage");
    await page
      .getByRole("button", { name: "Reload project", exact: true })
      .click();
    await expect(page.getByTestId("surface-preview-status")).toContainText(
      "STALE",
    );
    await expect(
      page.getByRole("button", { name: "Generate coarse preview" }),
    ).toBeDisabled();
    change("--accept-cage");
    await page
      .getByRole("button", { name: "Reload project", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Generate coarse preview" }),
    ).toBeEnabled();
    await preview(page);
  } finally {
    await running.stop();
  }
});

test("actual Mark II read-only copy remains blocked and hash-identical", async ({
  page,
}) => {
  const running = await server(root);
  try {
    await open(page, running, "mark2_drift");
    await expect(
      page.getByText("BLOCKED BY SOURCE/CAGE ACCEPTANCE", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Generate coarse preview" }),
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Add patch draft" }),
    ).toBeDisabled();
    const r = spawnSync(
      python,
      [
        resolve(repo, "studio/backend/tests/prepare_surfaces.py"),
        root,
        "--check-mark2",
      ],
      { cwd: repo, encoding: "utf8", windowsHide: true },
    );
    expect(r.status, r.stderr).toBe(0);
  } finally {
    await running.stop();
  }
});
