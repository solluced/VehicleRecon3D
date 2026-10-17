import { test, expect } from "@playwright/test";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { readFileSync, appendFileSync, writeFileSync } from "node:fs";
import { repo, python, server, boot, saved } from "./harness";
const root = resolve(repo, `build/studio04-browser-${Date.now()}/projects`);
test.beforeAll(() => {
  const p = spawnSync(
    python,
    [resolve(repo, "studio/backend/tests/prepare_reconciliation.py"), root],
    { cwd: repo, encoding: "utf8", windowsHide: true },
  );
  if (p.status !== 0) throw new Error(p.stderr);
});
async function enter(page: any, s: any, name = "rectification_positive") {
  await boot(page, s);
  await page.getByRole("button", { name: new RegExp(name) }).click();
  await page.getByRole("button", { name: "Reference → Rectification" }).click();
  await page.getByRole("heading", { name: "Reconcile the source" }).waitFor();
}
async function fit(page: any) {
  await page.getByLabel("Candidate creator").fill("Browser inspector");
  const request = JSON.parse(
    readFileSync(resolve(root, "../positive-request.json"), "utf8"),
  );
  for (const a of request.anchors.filter(
    (a: any) => a.role === "FIT" && !a.locked,
  )) {
    const row = page
      .getByLabel("Anchor table")
      .getByRole("row")
      .filter({ has: page.locator(`input[value="${a.observation_id}"]`) });
    await row.getByRole("combobox").selectOption("FIT");
  }
  await page
    .getByRole("button", { name: "Generate Candidate", exact: true })
    .click();
  await expect(page.getByLabel("Candidate decision")).toContainText(
    "ELIGIBLE_FOR_ACTIVATION",
  );
}
test("positive manual candidate, graphs, independent evidence, explicit activation and exact undo", async ({
  page,
}) => {
  const s = await server(root, false);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  try {
    await enter(page, s);
    const before = readFileSync(
      resolve(root, "positive/generated/calibration.json"),
    );
    const count = await page.getByLabel(/^Semantic \d+$/).count();
    await page.getByRole('button',{name:'Add anchor',exact:true}).click();
    const handle=page.getByTestId(`anchor-handle-${count}`);
    const box=(await handle.boundingBox())!;
    const value=await page.getByLabel(`Source normalized ${count}`,{exact:true}).inputValue();
    await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+20,box.y+box.height/2,{steps:4});await page.mouse.up();
    await expect(page.getByLabel(`Source normalized ${count}`,{exact:true})).not.toHaveValue(value);
    await page.getByLabel(`Remove anchor ${count}`,{exact:true}).click();
    await fit(page);
    await expect(
      page.getByRole("img", { name: "Mapping graph", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("img", { name: "Derivative / local-scale graph" }),
    ).toBeVisible();
    await expect(page.getByLabel("Held-out residual report")).toContainText(
      "PASS",
    );
    await page.getByRole('button',{name:'Generate Candidate',exact:true}).click();
    await expect(page.getByLabel(/^Compare /)).toHaveCount(2);
    for(const checkbox of await page.getByLabel(/^Compare /).all())await checkbox.check();
    await expect(page.getByLabel('Candidate comparison')).toBeVisible();
    await page.getByRole('img',{name:'Mapping graph',exact:true}).scrollIntoViewIfNeeded();
    await page.screenshot({path:resolve(repo,'build/studio04-rectification-positive.png')});
    await expect(
      page.getByRole("button", { name: "ACTIVATE RECTIFICATION", exact: true }),
    ).toBeDisabled();
    await page.getByLabel("Confirm rectification activation").check();
    await page
      .getByRole("button", { name: "ACTIVATE RECTIFICATION", exact: true })
      .click();
    await saved(page);
    await expect(page.getByLabel("Candidate decision")).toContainText("ACTIVE");
    expect(
      readFileSync(resolve(root, "positive/generated/calibration.json")).equals(
        before,
      ),
    ).toBe(false);
    await page
      .getByRole("button", { name: "Undo rectification / replacement" })
      .click();
    await saved(page);
    await expect
      .poll(() =>
        readFileSync(
          resolve(root, "positive/generated/calibration.json"),
        ).equals(before),
      )
      .toBe(true);
    expect(errors).toEqual([]);
  } finally {
    await s.stop();
  }
});
test("Mark II rejected candidate is visibly excessive, immutable and cannot activate", async ({
  page,
}) => {
  const s = await server(root, false);
  const files = [
    "project.json",
    "generated/calibration.json",
    "validation/rectification_candidate.json",
    "validation/rectification_magnitude.json",
  ];
  const before = files.map((f) => readFileSync(resolve(root, "mark2", f)));
  try {
    await enter(page, s, "mark2");
    await expect(page.getByLabel("Candidate decision")).toContainText(
      "REJECTED · NOT ACTIVE",
    );
    await expect(page.getByLabel("Candidate decision")).toContainText(
      "OUTSIDE SCALE LIMIT",
    );
    await expect(page.getByLabel("Candidate decision")).toContainText(
      "0.518261866",
    );
    await expect(page.getByLabel("Candidate decision")).toContainText(
      "2.150011985",
    );
    await expect(
      page.getByRole("button", { name: "ACTIVATE RECTIFICATION", exact: true }),
    ).toBeDisabled();
    await page.getByRole('img',{name:'Derivative / local-scale graph'}).scrollIntoViewIfNeeded();
    await page.screenshot({path:resolve(repo,'build/studio04-mark2-rejected.png')});
    files.forEach((f, i) =>
      expect(readFileSync(resolve(root, "mark2", f)).equals(before[i])).toBe(
        true,
      ),
    );
  } finally {
    await s.stop();
  }
});
test("stale calibration fences activation and requires regeneration", async ({
  page,
}) => {
  const s = await server(root, false);
  try {
    await enter(page, s);
    await fit(page);
    appendFileSync(resolve(root, "positive/generated/calibration.json"), "\n");
    await page
      .getByRole("button", { name: "Refresh evidence", exact: true })
      .click();
    await expect(page.getByLabel("Candidate decision")).toContainText("STALE");
    await page.getByLabel("Confirm rectification activation").check();
    await expect(
      page.getByRole("button", { name: "ACTIVATE RECTIFICATION", exact: true }),
    ).toBeDisabled();
  } finally {
    await s.stop();
  }
});
test("replacement preserves old source and world and displays unmeasured transfer proposals", async ({
  page,
}) => {
  const s = await server(root, false);
  try {
    await enter(page, s);
    const old = readFileSync(resolve(root, "positive/input/reference.png")),
      world = readFileSync(resolve(root, "positive/generated/cage.json"));
    const file = resolve(root, "../replacement.png");
    writeFileSync(file, Buffer.concat([old, Buffer.from("\nreplacement\n")]));
    await page.getByLabel("Confirm source replacement").check();
    await page
      .getByLabel("Replacement source image", { exact: true })
      .setInputFiles(file);
    await saved(page);
    await expect(
      page.getByRole("status").filter({ hasText: "CALIBRATION REQUIRED" }),
    ).toBeVisible();
    await expect(
      page.getByLabel("Source replacement comparison"),
    ).toContainText("PROPOSAL ONLY");
    expect(
      readFileSync(resolve(root, "positive/input/reference.png")).equals(old),
    ).toBe(true);
    expect(
      readFileSync(resolve(root, "positive/generated/cage.json")).equals(world),
    ).toBe(true);
    await expect(
      page.getByRole("button", { name: "Generate Candidate", exact: true }),
    ).toBeDisabled();
  } finally {
    await s.stop();
  }
});
