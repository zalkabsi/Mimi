import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Backend base URL comes from VITE_API_BASE (see README); default is the
// local FastAPI dev server.
export default defineConfig(({ mode }) => ({
  base: process.env.VITE_BASE_PATH || (mode === "demo" ? "./" : "/"),
  plugins: [react(), tailwindcss(), {
    name: "mimi-demo-manifest",
    generateBundle() {
      if (mode === "demo") this.emitFile({
        type: "asset",
        fileName: "demo-manifest.json",
        source: JSON.stringify({ mode: "read-only-replay", provider_calls: false, fixture_report_id: "mock0000demo" }, null, 2),
      });
    },
  }],
  define: mode === "demo" ? {
    "import.meta.env.VITE_USE_MOCK": JSON.stringify("1"),
    "import.meta.env.VITE_ROUTER_MODE": JSON.stringify("hash"),
  } : undefined,
  server: {
    port: 5173,
    strictPort: true,
  },
}));
