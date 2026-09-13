/**
 * Command permission levels corresponding to Bedrock server authorization tiers.
 */
export const CommandPermissionLevel = Object.freeze({
  Any: 0,
  GameDirectors: 1,
  Admin: 2,
  Host: 3,
  Owner: 4,
});

/**
 * Execution source origin types.
 */
export const CustomCommandSource = Object.freeze({
  Block: 'Block',
  Entity: 'Entity',
  NPCDialogue: 'NPCDialogue',
  Server: 'Server',
});

/**
 * Custom command execution status outcome.
 */
export const CustomCommandStatus = Object.freeze({
  Success: 0,
  Failure: 1,
});
