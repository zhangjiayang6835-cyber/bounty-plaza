import { world, system } from '@minecraft/server';
import { registerInspectCommand } from './commands/inspect';

// This is the main entry point for your behavior pack scripts.
// It's good practice to initialize your modules here.

system.run(() => {
    world.sendMessage("§aBehavior Pack scripts started!");

    // Initialize custom commands
    registerInspectCommand(); // Call the registration function for the inspect command
});

// Example: Listen for player join event
world.afterEvents.playerSpawn.subscribe(event => {
    const player = event.player;
    if (event.initialSpawn) {
        player.sendMessage(`§bWelcome, ${player.name}!`);
    }
});
