import {
  CommandPermissionLevel,
  CustomCommandSource,
  CustomCommandStatus,
  InspectionReport,
} from './types.js';

export interface Vector3 {
  x: number;
  y: number;
  z: number;
}

export interface ScriptEntity {
  id: string;
  typeId: string;
  name?: string;
  location?: Vector3;
}

export interface ScriptBlock {
  typeId: string;
  location: Vector3;
}

export interface CustomCommandOrigin {
  sourceType: CustomCommandSource | string;
  sourceEntity?: ScriptEntity;
  sourceBlock?: ScriptBlock;
  permissionLevel?: CommandPermissionLevel | number;
}

export interface CustomCommandResult {
  status: CustomCommandStatus;
  message: string;
}

export interface CustomCommand {
  name: string;
  description: string;
  permissionLevel: CommandPermissionLevel;
  cheatsRequired?: boolean;
}

export interface CustomCommandRegistry {
  registerCommand(
    commandDefinition: CustomCommand | string,
    callbackOrOptions?: unknown,
    maybeCallback?: unknown
  ): void;
}

export interface StartupEvent {
  customCommandRegistry: CustomCommandRegistry;
}

/**
 * Builds an inspection report summarizing the command execution context.
 *
 * @param origin Contextual origin metadata for the command invocation.
 * @returns Structured inspection report object.
 */
export function buildInspectionReport(
  origin: CustomCommandOrigin
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
    sourceType: origin.sourceType || CustomCommandSource.Server,
    timestamp: Date.now(),
  };
}

/**
 * Executes administrative inspection command logic across player and server contexts.
 *
 * @param origin Invocation metadata identifying caller type and position.
 * @returns Result object containing execution status and response message.
 */
export function executeInspectCommand(
  origin: CustomCommandOrigin
): CustomCommandResult {
  if (
    origin.permissionLevel !== undefined &&
    origin.permissionLevel < CommandPermissionLevel.Admin
  ) {
    return {
      status: CustomCommandStatus.Failure,
      message: '[EngineInspect] Permission denied: Admin clearance required.',
    };
  }

  const report = buildInspectionReport(origin);

  if (origin.sourceType === CustomCommandSource.Entity && origin.sourceEntity) {
    const entity = origin.sourceEntity;
    const isPlayer = entity.typeId === 'minecraft:player';
    const name = isPlayer && entity.name ? entity.name : entity.typeId;
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
 * Extracts and validates the active CustomCommandRegistry instance.
 *
 * @param target StartupEvent or CustomCommandRegistry instance.
 * @returns Validated CustomCommandRegistry instance.
 */
export function resolveRegistry(target: unknown): CustomCommandRegistry {
  if (!target || typeof target !== 'object') {
    throw new TypeError(
      'Invalid argument: expected StartupEvent or CustomCommandRegistry instance.'
    );
  }

  const candidate =
    'customCommandRegistry' in target
      ? (target as StartupEvent).customCommandRegistry
      : (target as CustomCommandRegistry);

  if (!candidate || typeof candidate.registerCommand !== 'function') {
    throw new TypeError(
      'CustomCommandRegistry instance with registerCommand method is required.'
    );
  }

  return candidate;
}

/**
 * Registers the /inspect and /engine:inspect slash commands onto the startup registry.
 *
 * @param target The startup event or CustomCommandRegistry instance.
 */
export function registerInspectCommand(
  target: StartupEvent | CustomCommandRegistry | unknown
): void {
  const registry = resolveRegistry(target);

  const inspectCommandDefinition: CustomCommand = {
    name: 'inspect',
    description: 'Inspect administrative engine status and entity metrics',
    permissionLevel: CommandPermissionLevel.Admin,
    cheatsRequired: true,
  };

  registry.registerCommand(
    inspectCommandDefinition,
    (origin: CustomCommandOrigin): CustomCommandResult => {
      return executeInspectCommand(origin);
    }
  );

  const engineInspectDefinition: CustomCommand = {
    name: 'engine:inspect',
    description: 'Inspect administrative engine status and entity metrics',
    permissionLevel: CommandPermissionLevel.Admin,
    cheatsRequired: true,
  };

  registry.registerCommand(
    engineInspectDefinition,
    (origin: CustomCommandOrigin): CustomCommandResult => {
      return executeInspectCommand(origin);
    }
  );
}
