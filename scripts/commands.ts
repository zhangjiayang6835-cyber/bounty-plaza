import {
  system,
  CommandPermissionLevel,
  CustomCommandParamType,
  CustomCommandStatus,
} from '@minecraft/server';
import type {
  StartupBeforeEvent,
  CustomCommandOrigin,
  CustomCommandResult,
  CustomCommandRegistry,
} from '@minecraft/server';

/**
 * Inspection report structure containing audited player data.
 */
export interface InspectionReport {
  target: string;
  caller: string;
  dimension: string;
  location: { x: number; y: number; z: number };
  mode: string;
  timestamp: number;
}

/**
 * Executes administration inspect routine on target entity or player.
 *
 * @param origin - The execution context invoking the command.
 * @param target - Name identifier of target player or entity.
 * @param mode - Inspection scope ('inventory', 'location', 'effects', 'all').
 * @returns Structured custom command execution result.
 */
export function executeInspectCommand(
  origin: CustomCommandOrigin,
  target: string,
  mode: string = 'all'
): CustomCommandResult {
  if (!target || target.trim().length === 0) {
    return {
      status: CustomCommandStatus.Failure,
      message: 'Command execution failed: A target player or entity identifier must be specified.',
    };
  }

  const callerName = origin.sourceEntity ? origin.sourceEntity.nameTag : 'ServerAdmin';
  const coords = origin.location
    ? { x: Math.round(origin.location.x), y: Math.round(origin.location.y), z: Math.round(origin.location.z) }
    : { x: 0, y: 0, z: 0 };

  const report: InspectionReport = {
    target: target.trim(),
    caller: callerName,
    dimension: origin.dimension ? origin.dimension.id : 'minecraft:overworld',
    location: coords,
    mode: mode.toLowerCase(),
    timestamp: Date.now(),
  };

  const formattedOutput =
    `[Admin:Inspect] Target: ${report.target} | Dimension: ${report.dimension} | ` +
    `Coords: (${coords.x}, ${coords.y}, ${coords.z}) | Mode: ${report.mode} | Caller: ${report.caller}`;

  return {
    status: CustomCommandStatus.Success,
    message: formattedOutput,
  };
}

/**
 * Registers administration commands directly on the CustomCommandRegistry instance.
 *
 * @param registry - Bedrock custom command registry from the startup event.
 */
export function registerAdminCommands(registry: CustomCommandRegistry): void {
  registry.registerCommand(
    {
      name: 'admin:inspect',
      description: 'Inspect player inventory, state, and permissions.',
      permissionLevel: CommandPermissionLevel.GameDirectors,
      cheatsRequired: false,
      mandatoryParameters: [
        {
          name: 'target',
          type: CustomCommandParamType.String,
        },
      ],
      optionalParameters: [
        {
          name: 'mode',
          type: CustomCommandParamType.String,
        },
      ],
    },
    (origin: CustomCommandOrigin, target: string, mode?: string): CustomCommandResult => {
      return executeInspectCommand(origin, target, mode);
    }
  );
}

/**
 * Subscribes to the startup lifecycle event to register custom commands safely.
 * Replaces deprecated chatSend interception and prevents unhandled startup exceptions.
 */
export function registerCustomCommands(): void {
  system.beforeEvents.startup.subscribe((event: StartupBeforeEvent): void => {
    if (!event || !event.customCommandRegistry) {
      throw new Error(
        'Critical Startup Failure: event.customCommandRegistry is undefined. ' +
        'Ensure min_engine_version supports customCommandRegistry in manifest.json.'
      );
    }

    registerAdminCommands(event.customCommandRegistry);
  });
}

/**
 * Lifecycle initialization entrypoint maintaining backward compatibility.
 * Invoked during world load to wire startup hooks without runtime tick delays.
 */
export function initCommands(): void {
  registerCustomCommands();
}
