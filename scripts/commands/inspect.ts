import {
  system,
  world,
  CommandPermissionLevel,
  type CustomCommandRegistry,
} from "@minecraft/server";

/**
 * Administrative inspection slash command.
 *
 * Previously this crashed BDS at startup with:
 *   TypeError: CustomCommandRegistry.registerCommand is not a function
 *
 * `CustomCommandRegistry` is not a class with static methods — the registry
 * instance is only exposed on the `system.beforeEvents.startup` event.
 * Registration must happen inside that event, and execution is dispatched
 * through `system.afterEvents.customCommand`.
 */

const COMMAND_NAME = "tank:inspect";

/** Minimum permission required to run the command (documented enum). */
const REQUIRED_PERMISSION = CommandPermissionLevel.GameDirectors;

function registerInspectCommand(registry: CustomCommandRegistry): void {
  registry.registerCommand({
    name: COMMAND_NAME,
    description: "Inspect entity/player state for administration",
    permissionLevel: REQUIRED_PERMISSION,
    mandatoryParameters: [],
    optionalParameters: [],
  });
}

// Register during the startup before-event, using the registry instance
// provided by the event (NOT a static method on CustomCommandRegistry).
system.beforeEvents.startup.subscribe((event) => {
  registerInspectCommand(event.customCommandRegistry);
});

// Handle command execution via the stable after-event.
system.afterEvents.customCommand.subscribe((event) => {
  if (event.commandName !== COMMAND_NAME) {
    return;
  }

  const source = event.sourceEntity;

  // Runtime permission gating in addition to the registration-level gate.
  if (!source || source.typeId !== "minecraft:player") {
    return;
  }

  const player = world.getPlayers().find((p) => p.id === source.id);
  if (!player) {
    return;
  }

  // Only players at or above the required permission level may proceed.
  if ((player.commandPermissionLevel ?? 0) < REQUIRED_PERMISSION) {
    player.sendMessage(
      `§cYou do not have permission to run /${COMMAND_NAME} (requires level ${REQUIRED_PERMISSION}).`
    );
    return;
  }

  // --- Inspection logic ---
  const target = player.getBlockFromViewDirection()?.location;
  const entities = player.getEntitiesFromViewDirection();

  player.sendMessage(`§e--- Inspection: ${player.name} ---`);
  player.sendMessage(`§7Position: ${JSON.stringify(player.location)}`);
  player.sendMessage(`§7Dimension: ${player.dimension.id}`);
  if (target) {
    player.sendMessage(`§7View target block: ${JSON.stringify(target)}`);
  }
  for (const hit of entities) {
    const e = hit.entity;
    player.sendMessage(
      `§7Entity: ${e.typeId} (id: ${e.id}) at ${JSON.stringify(e.location)}`
    );
  }
});
