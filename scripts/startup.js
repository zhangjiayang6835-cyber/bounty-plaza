import { registerInspectCommand } from './commands/inspect.js';

/**
 * Subscribes all early-execution system lifecycle listeners and custom commands.
 *
 * @param systemInstance Optional Bedrock system singleton instance.
 */
export function initializeStartupHooks(systemInstance) {
  const targetSystem = systemInstance ?? globalThis.system;
  if (!targetSystem?.beforeEvents?.startup?.subscribe) {
    throw new Error('System instance with beforeEvents.startup.subscribe is required.');
  }

  targetSystem.beforeEvents.startup.subscribe((event) => {
    registerInspectCommand(event);
  });
}
