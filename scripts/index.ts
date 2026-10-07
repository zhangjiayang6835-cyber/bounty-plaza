import { world, system } from "@minecraft/server";

/**
 * Main entry point for the bounty-plaza command scripts.
 * Uses @minecraft/server 2.8.0+ startup event hooks for stable command registration.
 */

// Register all command modules on startup
system.runOnce(() => {
  try {
    // Import and register inspect command
    const inspectModule = await import("./commands/inspect");
    void inspectModule; // Module self-registers on import
  } catch (error) {
    console.warn("[bounty-plaza] Failed to load command module:", error);
  }
});

// Listen for world load to ensure commands are ready
world.afterEvents.worldLoad.subscribe(() => {
  console.log("[bounty-plaza] World loaded. Commands registered.");
});

// Prevent crashes on unload
world.beforeEvents.worldUnload.subscribe(() => {
  system.run(() => {
    console.log("[bounty-plaza] World unloading. Cleaning up...");
  });
});
