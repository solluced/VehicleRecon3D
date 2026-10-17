import { defineConfig } from "@playwright/test";
import base from "./playwright.config";
export default defineConfig({
  ...base,
  testDir: "release",
  timeout: 300000,
  reporter: [
    ["list"],
    [
      "json",
      {
        outputFile: "../../build/studio05-surface-memory-browser-results.json",
      },
    ],
  ],
});
