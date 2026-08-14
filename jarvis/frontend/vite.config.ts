import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8340",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/ws": {
        target: "http://127.0.0.1:8340",
        ws: true,
        changeOrigin: true,
      },
      "/debug": {
        target: "http://127.0.0.1:8340",
        changeOrigin: true,
      },
      "/voice": {
        target: "http://127.0.0.1:8340",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
  },
});
