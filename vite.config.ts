import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The companion UI talks to the backend at http://127.0.0.1:8787.
// During dev we proxy /api so SSE + uploads work without CORS surprises.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5273,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8787",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
