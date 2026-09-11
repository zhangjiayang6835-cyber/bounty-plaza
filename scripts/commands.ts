import {
  system,
} from '@minecraft/server';
import type {
  StartupBeforeEvent,
  CustomCommandOrigin,
  CustomCommandResult as McCustomCommandResult,
  CustomCommandRegistry,
} from '@minecraft/server';
import {
  CommandPermissionLevel,
  CustomCommandSource,
  CustomCommandStatus,
  InspectionReport,
  CustomCommand,
  CustomCommandResult,
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
  InspectionReport,
  CustomCommand,
  CustomCommandResult,
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
export function registerAdminCommands(registry: CustomCommandRegistry): void {
  registry.registerCommand(
    {
      name: 'engine:inspect',
      description: 'Inspect administrative engine status and entity metrics',
      permissionLevel: CommandPermissionLevel.Admin,
      cheatsRequired: true,
    },
    (origin: CustomCommandOrigin): McCustomCommandResult => {
      return executeInspectCommand(
        origin,
        CommandPermissionLevel.Admin
      ) as McCustomCommandResult;
    }
  );
}

/**
 * Subscribes to startup lifecycle event to register custom commands safely.
 */
export function registerCustomCommands(): void {
  system.beforeEvents.startup.subscribe((event: StartupBeforeEvent): void => {
    if (!event || !event.customCommandRegistry) {
      throw new Error('Critical Startup Failure: event.customCommandRegistry is undefined.');
    }
    registerAdminCommands(event.customCommandRegistry);
  });
}

/**
 * Lifecycle initialization entrypoint maintaining backward compatibility.
 */
export function initCommands(): void {
  registerCustomCommands();
}
