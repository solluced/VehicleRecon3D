import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
const windowsEdge =
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
export default defineConfig({
  testDir: "e2e",
  timeout: 120000,
  workers: 1,
  fullyParallel: false,
  reporter: [
    ["list"],
    ["json", { outputFile: "../../build/studio03-e2e-results.json" }],
  ],
  use: {
    headless: true,
    viewport: { width: 1500, height: 1000 },
    launchOptions: {
      executablePath:
        process.env.VEHICLERECON_BROWSER ||
        (existsSync(windowsEdge) ? windowsEdge : undefined),
      args: [
        "--no-first-run",
        "--js-flags=--expose-gc",
        ...(process.env.VEHICLERECON_SOFTWARE_GL === "1"
          ? ["--use-gl=angle", "--use-angle=swiftshader"]
          : []),
      ],
    },
    screenshot: "only-on-failure",
  },
});
