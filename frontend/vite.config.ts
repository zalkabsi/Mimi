import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Backend base URL comes from VITE_API_BASE (see README); default is the
// local FastAPI dev server.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
  },
});
