import { system, world, Player, CommandPermissionLevel } from '@minecraft/server';

/**
 * Registers the /inspect command and handles its execution.
 */
export function registerInspectCommand() {
    system.beforeEvents.scriptEventCommandSend.subscribe(event => {
        const { id, message, sourceEntity } = event;

        // Check if the command ID matches our custom command
        if (id === 'minecraft:inspect') {
            // Ensure the command was sent by a player
            if (sourceEntity instanceof Player) {
                const player = sourceEntity;
                const args = message.split(' '); // Split the message into arguments

                // Basic permission check: Only players with 'admin' tag can use this command
                // This is a common way to implement permission levels for script commands.
                // For a more robust system, you might use a custom permission API or scoreboards.
                if (!player.hasTag('admin')) {
                    player.sendMessage("§cYou do not have permission to use the /inspect command.");
                    event.cancel = true; // Cancel the event to prevent further processing
                    return;
                }

                // Example: Basic /inspect command logic
                // In a real scenario, you would parse args, get player's target block, etc.
                if (args.length === 0 || args[0] === '') {
                    player.sendMessage("§aUsage: /inspect [target]");
                    player.sendMessage("§7(Example: /inspect block, /inspect entity)");
                } else {
                    const target = args[0];
                    player.sendMessage(`§eInspecting: ${target}`);
                    // Add your actual inspection logic here.
                    // For example, getting the block the player is looking at:
                    // const block = player.getBlockFromViewDirection();
                    // if (block) {
                    //     player.sendMessage(`Block: ${block.typeId}, X:${block.x} Y:${block.y} Z:${block.z}`);
                    // } else {
                    //     player.sendMessage("No block in view.");
                    // }
                }

                event.cancel = true; // Crucial: Cancel the event to prevent the game from trying to process it as an unknown command.
            } else {
                // Command was sent by a non-player entity or console (if applicable)
                world.sendMessage(`§cThe /inspect command can only be used by players.`);
                event.cancel = true;
            }
        }
    });

    world.sendMessage("§a/inspect command registered successfully.");
}

// Call the registration function immediately when the module is loaded
// This ensures the event listener is set up as soon as the script starts.
system.run(() => {
    registerInspectCommand();
});
