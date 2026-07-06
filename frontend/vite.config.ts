import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Vite serves the SPA from /.
// During development we expect a `public/manifest.json` next to this config;
// the Python pipeline (tools/emit_manifest.py --out frontend/public/manifest.json)
// writes one. Per-issue manifests live under public/browse/... and the Vite
// dev server streams them as static files.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    strictPort: false,
    // The Python pipeline drops JSON files under reports/, which the
    // dev server can serve from frontend/public/ via a symlink. As a
    // convenience for hacking, we just enable CORS so the SPA can fetch
    // directly from a sibling dev server.
    cors: true,
  },
  build: {
    target: "es2022",
    sourcemap: true,
    outDir: "dist",
  },
});