import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    // @asctp/parabola is a workspace-linked package, so Vite treats it as source and
    // doesn't crawl into its own dependencies during the initial scan. Without this, the
    // first real page load pays for pre-bundling these (large) transitive deps on demand,
    // adding several extra seconds before the app is actually usable.
    include: ["@stellar/stellar-sdk", "viem"],
  },
});
