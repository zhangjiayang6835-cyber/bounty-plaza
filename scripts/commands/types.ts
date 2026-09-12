/**
 * Command permission levels corresponding to Bedrock server authorization tiers.
 */
export enum CommandPermissionLevel {
  Any = 0,
  Normal = 0,
  GameDirectors = 1,
  Operator = 1,
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
 * Inspection target descriptor summarizing inspected entity or server state.
 */
export interface InspectionReport {
  targetType: string;
  targetId?: string;
  sourceType: string;
  coordinates?: {
    x: number;
    y: number;
    z: number;
  };
  timestamp: number;
}
