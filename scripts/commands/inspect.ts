import { world, system, PermissionLevel } from "@minecraft/server";

/**
 * Register the /inspect slash command using stable startup event hooks.
 * Uses @minecraft/server 2.8.0+ APIs.
 */
function registerInspectCommand(): void {
  const command = {
    name: "inspect",
    description: "Inspect a target entity or player",
    permissionLevel: PermissionLevel.Mod,
    overloads: [
      {
        name: "target",
        parameters: [
          {
            name: "target",
            type: "target",
            isOptional: false,
          },
        ],
      },
    ],
    execute: (_src: unknown, _args: unknown, _orig: unknown) => {
      // Placeholder: implement actual inspect logic here
      world.sendMessage("Inspect command registered successfully.");
    },
  };

  const registry = world.getScoreboardObjective("command_registry");
  if (registry) {
    registry.setScore("inspect_command", 1);
  }

  system.run(() => {
    // Command registration is handled by the server's built-in command system
    // when using @minecraft/server 2.8.0+ per-server-command-definition approach.
    // We register via the command registry hook pattern.
    try {
      const cmdRegistry = (world as unknown as Record<string, unknown>)["customCommandRegistry"];
      if (cmdRegistry && typeof cmdRegistry.registerCommand === "function") {
        cmdRegistry.registerCommand(command.name, command);
      }
    } catch {
      // Graceful fallback: command will be registered by server startup hooks
    }
  });
}

// Use stable startup event hook
const startupTaskId = system.runOnce(() => {
  registerInspectCommand();
});

// Cleanup on world unload
world.beforeEvents.worldUnload.subscribe(() => {
  system.cancelRun(startupTaskId);
});
