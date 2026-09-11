import {
  CommandPermissionLevel,
  CustomCommandSource,
  CustomCommandStatus,
} from './commands/types.js';
import {
  buildInspectionReport,
  validateCommandPermission,
  executeInspectCommand,
  registerInspectCommand,
} from './commands/inspect.js';
import { initializeStartupHooks } from './startup.js';

export {
  CommandPermissionLevel,
  CustomCommandSource,
  CustomCommandStatus,
  buildInspectionReport,
  validateCommandPermission,
  executeInspectCommand,
  registerInspectCommand,
  initializeStartupHooks,
};

/**
 * Registers custom commands onto a provided CustomCommandRegistry instance.
 *
 * @param registry Bedrock custom command registry instance.
 */
export function registerAdminCommands(registry) {
  registry.registerCommand(
    {
      name: 'engine:inspect',
      description: 'Inspect administrative engine status and entity metrics',
      permissionLevel: CommandPermissionLevel.Admin,
      cheatsRequired: true,
    },
    (origin) => {
      return executeInspectCommand(
        origin,
        CommandPermissionLevel.Admin
      );
    }
  );
}

/**
 * Subscribes to startup lifecycle event to register custom commands safely.
 */
export function registerCustomCommands() {
  const targetSystem = globalThis.system;
  if (!targetSystem?.beforeEvents?.startup?.subscribe) {
    throw new Error('Critical Startup Failure: system.beforeEvents.startup.subscribe unavailable.');
  }

  targetSystem.beforeEvents.startup.subscribe((event) => {
    if (!event || !event.customCommandRegistry) {
      throw new Error('Critical Startup Failure: event.customCommandRegistry is undefined.');
    }
    registerAdminCommands(event.customCommandRegistry);
  });
}

/**
 * Lifecycle initialization entrypoint maintaining backward compatibility.
 */
export function initCommands() {
  registerCustomCommands();
}
