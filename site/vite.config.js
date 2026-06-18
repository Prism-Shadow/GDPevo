import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/GDPevo/",
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
