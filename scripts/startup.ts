import { registerInspectCommand, StartupEvent } from './commands/inspect.js';

export interface SystemBeforeEvents {
  startup: {
    subscribe(callback: (event: StartupEvent) => void): void;
  };
}

export interface BedrockSystem {
  beforeEvents: SystemBeforeEvents;
}

/**
 * Subscribes all early-execution system lifecycle listeners and custom commands.
 *
 * @param system Optional Bedrock system object instance.
 */
export function initializeStartupHooks(system?: BedrockSystem): void {
  if (system && system.beforeEvents && system.beforeEvents.startup) {
    system.beforeEvents.startup.subscribe((event: StartupEvent) => {
      registerInspectCommand(event);
    });
  }
}
