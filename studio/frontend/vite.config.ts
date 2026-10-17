import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../backend/src/vehiclerecon_studio/static",
    emptyOutDir: true,
  },
  server: { host: "127.0.0.1" },
});
