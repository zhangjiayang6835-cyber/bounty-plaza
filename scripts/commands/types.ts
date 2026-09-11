/**
 * Command permission levels corresponding to Bedrock server authorization tiers.
 */
export enum CommandPermissionLevel {
  Any = 0,
  GameDirectors = 1,
  Admin = 2,
  Host = 3,
  Owner = 4,
}

/**
 * Execution source origin types.
 */
export enum CustomCommandSource {
  Block = 'Block',
  Entity = 'Entity',
  NPCDialogue = 'NPCDialogue',
  Server = 'Server',
}

/**
 * Custom command execution status outcome.
 */
export enum CustomCommandStatus {
  Success = 0,
  Failure = 1,
}

/**
 * Coordinates in 3-dimensional Bedrock world space.
 */
export interface CommandCoordinates {
  x: number;
  y: number;
  z: number;
}

/**
 * Inspection target descriptor summarizing inspected entity or server state.
 */
export interface InspectionReport {
  targetType: string;
  targetId?: string;
  sourceType: CustomCommandSource;
  coordinates?: CommandCoordinates;
  timestamp: number;
}

/**
 * Generic interface for command registration parameters.
 */
export interface CustomCommandParameter {
  name: string;
  type: string;
}

/**
 * Specification structure for custom command registration.
 */
export interface CustomCommand {
  name: string;
  description: string;
  permissionLevel: CommandPermissionLevel;
  cheatsRequired?: boolean;
  mandatoryParameters?: CustomCommandParameter[];
  optionalParameters?: CustomCommandParameter[];
}

/**
 * Result payload returned from command callback execution.
 */
export interface CustomCommandResult {
  message?: string;
  status: CustomCommandStatus;
}
