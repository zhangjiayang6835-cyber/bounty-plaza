import { registerInspectCommand } from './commands/inspect.js';
/**
 * Subscribes all early-execution system lifecycle listeners and custom commands.
 *
 * @param system Optional Bedrock system object instance.
 */
export function initializeStartupHooks(system) {
    if (system && system.beforeEvents && system.beforeEvents.startup) {
        system.beforeEvents.startup.subscribe((event) => {
            registerInspectCommand(event);
        });
    }
}
