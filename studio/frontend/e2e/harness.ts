import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { randomBytes } from "node:crypto";
import type { Page } from "@playwright/test";
export const repo = resolve("../.."),
  python =
    process.env.VEHICLERECON_PYTHON ||
    resolve(
      repo,
      process.platform === "win32"
        ? ".venv/Scripts/python.exe"
        : ".venv/bin/python",
    );
export async function server(
  root: string,
  cv_enabled = true,
): Promise<{
  origin: string;
  secret: string;
  pid: number;
  stop: () => Promise<void>;
}> {
  const secret = randomBytes(32).toString("hex");
  const process = spawn(
    python,
    [resolve(repo, "studio/backend/tests/browser_server.py")],
    { cwd: repo, stdio: ["pipe", "pipe", "pipe"], windowsHide: true },
  );
  process.stdin!.end(JSON.stringify({ root, secret, cv_enabled }) + "\n");
  const info = await new Promise<{ origin: string; pid: number }>(
    (ok, fail) => {
      let text = "";
      process.stdout!.on("data", (b) => {
        text += b;
        try {
          ok(JSON.parse(text.trim()));
        } catch {}
      });
      process.once("error", fail);
      process.stderr!.on("data", (b) => {
        if (String(b).includes("Traceback"))
          fail(new Error("Browser test backend failed to start"));
      });
    },
  );
  const origin = info.origin;
  for (let i = 0; i < 100; i++) {
    try {
      await fetch(origin);
      break;
    } catch {
      await new Promise((r) => setTimeout(r, 50));
    }
  }
  return {
    origin,
    secret,
    pid: info.pid,
    stop: async () => {
      if (process.exitCode !== null || process.signalCode !== null) return;
      if (globalThis.process.platform === "win32") {
        spawnSync("taskkill", ["/PID", String(process.pid), "/T", "/F"], {
          windowsHide: true,
          timeout: 10000,
        });
        return;
      }
      const exit = new Promise<void>((r) => process.once("exit", () => r()));
      process.kill();
      await Promise.race([exit, new Promise<void>((r) => setTimeout(r, 5000))]);
    },
  };
}
export function rss(pid: number) {
  const result = spawnSync(
    python,
    [resolve(repo, "studio/backend/tests/process_memory.py"), String(pid)],
    { cwd: repo, encoding: "utf-8", windowsHide: true },
  );
  if (result.status !== 0) throw new Error(result.stderr);
  return Number(result.stdout.trim());
}
export function prepare(root: string, performance = false) {
  mkdirSync(resolve(root, ".."), { recursive: true });
  const result = spawnSync(
    python,
    [
      resolve(repo, "studio/backend/tests/prepare_browser.py"),
      root,
      ...(performance ? ["--performance"] : []),
    ],
    { cwd: repo, encoding: "utf-8", windowsHide: true },
  );
  if (result.status !== 0) throw new Error(result.stderr);
}
export async function boot(page: Page, s: { origin: string; secret: string }) {
  await page.goto(s.origin + "/#bootstrap=" + s.secret);
  await page.getByRole("heading", { name: "Start with the source." }).waitFor();
}
export async function snapshot(page: Page, name?: string) {
  return page.evaluate(async (name) => {
    const headers = { "X-Studio-Tab": sessionStorage.getItem("vr-tab")! };
    const projects = await (
      await fetch("/api/v1/projects", { headers })
    ).json();
    const p = projects.find((p: any) =>
      name
        ? p.project?.asset_name === name
        : p.project?.asset_name === "Manual_Study",
    );
    if (!p) throw new Error("Test project unavailable");
    return (await fetch("/api/v1/projects/" + p.id, { headers })).json();
  }, name);
}
export async function camera(page: Page) {
  return JSON.parse(
    (await page.getByTestId("canvas").getAttribute("data-viewport")) || "{}",
  );
}
export async function saved(page: Page) {
  await page
    .locator(".save-state")
    .filter({ hasText: /^Saved$/ })
    .waitFor();
}
