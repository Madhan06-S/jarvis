import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    host: "0.0.0.0",
    allowedHosts: true,
    proxy: {
      "/ws": {
        target: "http://127.0.0.1:8340",
        ws: true,
        secure: false,
      },
      "/api": {
        target: "http://127.0.0.1:8340",
        secure: false,
      },
    },
  },
  build: {
    outDir: "dist",
    target: "es2020",
    minify: "esbuild",
    cssMinify: true,
    sourcemap: false,
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          core: ["./src/performance-manager.ts", "./src/ws.ts", "./src/terminal-stream.ts"],
          orb: ["./src/orb.ts"],
          voice: ["./src/voice.ts"],
        },
      },
    },
  },
  optimizeDeps: {
    include: [],
  },
});
