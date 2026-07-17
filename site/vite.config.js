import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  base: "/GDPevo/",
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        index: resolve(__dirname, "index.html"),
        blog: resolve(__dirname, "blog.html"),
        selfEvolution: resolve(__dirname, "blog-self-evolution.html"),
        releaseNote: resolve(__dirname, "release-note.html")
      }
    }
  }
});
