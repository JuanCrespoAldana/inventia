/// <reference types="vitest/config" />
import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

const API = process.env.VITE_PROXY_API ?? "http://localhost:8000";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: { "/api": { target: API, changeOrigin: true } },
  },
  preview: {
    port: 4173,
    proxy: { "/api": { target: API, changeOrigin: true } },
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (!id.includes("node_modules")) return undefined;
          if (/react-router|react-dom|[\\/]react[\\/]|scheduler/.test(id)) return "vendor";
          if (id.includes("framer-motion") || id.includes("motion-dom") || id.includes("motion-utils")) return "animacion";
          if (id.includes("@tanstack") || id.includes("axios")) return "datos";
          return undefined;
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
