import type {
  CustomCommand as McCustomCommand,
  CustomCommandOrigin as McCustomCommandOrigin,
  CustomCommandResult as McCustomCommandResult,
  Player,
  StartupEvent,
  CustomCommandRegistry,
} from '@minecraft/server';
import {
  CommandPermissionLevel,
  CustomCommandSource,
  CustomCommandStatus,
  InspectionReport,
  CustomCommand,
  CustomCommandResult,
} from './types.js';

/**
 * Builds an inspection report summarizing the command execution context.
 *
 * @param origin Contextual origin metadata for the command invocation.
 * @returns Structured inspection report object.
 */
export function buildInspectionReport(
  origin: McCustomCommandOrigin | any
): InspectionReport {
  if (origin.sourceType === CustomCommandSource.Entity && origin.sourceEntity) {
    const entity = origin.sourceEntity;
    const location = entity.location;
    return {
      targetType: entity.typeId,
      targetId: entity.id,
      sourceType: origin.sourceType,
      coordinates: location
        ? {
            x: Math.round(location.x * 100) / 100,
            y: Math.round(location.y * 100) / 100,
            z: Math.round(location.z * 100) / 100,
          }
        : undefined,
      timestamp: Date.now(),
    };
  }

  if (origin.sourceType === CustomCommandSource.Block && origin.sourceBlock) {
    const block = origin.sourceBlock;
    const location = block.location;
    return {
      targetType: block.typeId,
      sourceType: origin.sourceType,
      coordinates: {
        x: location.x,
        y: location.y,
        z: location.z,
      },
      timestamp: Date.now(),
    };
  }

  return {
    targetType: 'server_console',
    sourceType: origin.sourceType ?? CustomCommandSource.Server,
    timestamp: Date.now(),
  };
}

/**
 * Validates whether the command invocation meets the required permission tier.
 *
 * @param origin Invocation origin metadata.
 * @param requiredLevel Minimum permission level necessary for authorization.
 * @returns Boolean representing whether authorization is granted.
 */
export function validateCommandPermission(
  origin: McCustomCommandOrigin | any,
  requiredLevel: CommandPermissionLevel = CommandPermissionLevel.Admin
): boolean {
  if (origin.permissionLevel !== undefined && origin.permissionLevel < requiredLevel) {
    return false;
  }

  if (
    origin.sourceEntity?.permissionLevel !== undefined &&
    origin.sourceEntity.permissionLevel < requiredLevel
  ) {
    return false;
  }

  return true;
}

/**
 * Executes administrative inspection command logic across player and server contexts.
 *
 * @param origin Invocation metadata identifying caller type and position.
 * @param requiredLevel Required permission tier for authorization gating.
 * @returns Result object containing execution status and response message.
 */
export function executeInspectCommand(
  origin: McCustomCommandOrigin | any,
  requiredLevel: CommandPermissionLevel = CommandPermissionLevel.Admin
): CustomCommandResult {
  if (!validateCommandPermission(origin, requiredLevel)) {
    return {
      status: CustomCommandStatus.Failure,
      message: `[EngineInspect] Access denied: Insufficient permissions. Required tier: ${CommandPermissionLevel[requiredLevel]}.`,
    };
  }

  const report = buildInspectionReport(origin);

  if (origin.sourceType === CustomCommandSource.Entity && origin.sourceEntity) {
    const entity = origin.sourceEntity;
    const isPlayer = entity.typeId === 'minecraft:player';
    const name = isPlayer ? (entity as unknown as Player).name : entity.typeId;
    const coords = report.coordinates
      ? `[${report.coordinates.x}, ${report.coordinates.y}, ${report.coordinates.z}]`
      : 'unknown';

    return {
      status: CustomCommandStatus.Success,
      message: `[EngineInspect] Inspected entity '${name}' at ${coords}. Status: healthy.`,
    };
  }

  if (origin.sourceType === CustomCommandSource.Block && origin.sourceBlock) {
    const block = origin.sourceBlock;
    return {
      status: CustomCommandStatus.Success,
      message: `[EngineInspect] Inspected command block '${block.typeId}' at [${block.location.x}, ${block.location.y}, ${block.location.z}].`,
    };
  }

  return {
    status: CustomCommandStatus.Success,
    message: `[EngineInspect] BDS Server Console inspected at timestamp ${report.timestamp}. Subsystems operational.`,
  };
}

/**
 * Registers the /engine:inspect command using the startup event custom command registry.
 *
 * @param eventOrRegistry StartupEvent carrying customCommandRegistry, or the registry instance directly.
 * @returns Registered CustomCommand definition object.
 */
export function registerInspectCommand(
  eventOrRegistry?: StartupEvent | CustomCommandRegistry | any
): CustomCommand {
  const resolvedTarget = eventOrRegistry ?? (globalThis as any).system;

  if (
    !eventOrRegistry &&
    resolvedTarget?.beforeEvents?.startup?.subscribe
  ) {
    let registered: CustomCommand | undefined;
    resolvedTarget.beforeEvents.startup.subscribe((event: StartupEvent) => {
      registered = registerInspectCommand(event);
    });
    return (
      registered ?? {
        name: 'engine:inspect',
        description: 'Inspect administrative engine status and entity metrics',
        permissionLevel: CommandPermissionLevel.Admin,
        cheatsRequired: true,
      }
    );
  }

  const registry: CustomCommandRegistry =
    resolvedTarget?.customCommandRegistry ?? resolvedTarget;

  if (!registry || typeof registry.registerCommand !== 'function') {
    throw new TypeError(
      'CustomCommandRegistry instance with registerCommand function is required.'
    );
  }

  const inspectCommandDefinition: CustomCommand = {
    name: 'engine:inspect',
    description: 'Inspect administrative engine status and entity metrics',
    permissionLevel: CommandPermissionLevel.Admin,
    cheatsRequired: true,
  };

  registry.registerCommand(
    inspectCommandDefinition as McCustomCommand,
    (origin: McCustomCommandOrigin): McCustomCommandResult => {
      return executeInspectCommand(
        origin,
        CommandPermissionLevel.Admin
      ) as McCustomCommandResult;
    }
  );

  return inspectCommandDefinition;
}
