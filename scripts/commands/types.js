/**
 * Command permission levels corresponding to Bedrock server authorization tiers.
 */
export const CommandPermissionLevel = {
  Any: 0,
  GameDirectors: 1,
  Admin: 2,
  Host: 3,
  Owner: 4,
};

/**
 * Execution source origin types.
 */
export const CustomCommandSource = {
  Block: 'Block',
  Entity: 'Entity',
  NPCDialogue: 'NPCDialogue',
  Server: 'Server',
};

/**
 * Custom command execution status outcome.
 */
export const CustomCommandStatus = {
  Success: 0,
  Failure: 1,
};
