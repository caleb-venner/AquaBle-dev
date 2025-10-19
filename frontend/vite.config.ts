import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  root: ".",
  base: "./", // Use relative paths for assets to support Ingress base paths
  server: {
    port: 5173,
    host: "0.0.0.0",
    open: true,
    proxy: {
      "/api": "http://localhost:8000"
    }
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        "test-hub": resolve(__dirname, "tests/test-hub.html"),
        "percentages-test": resolve(__dirname, "tests/percentages-test.html"),
        "wattage-test": resolve(__dirname, "tests/wattage-test.html")
      }
    }
  }
});
