/**
 * Command permission levels corresponding to Bedrock server authorization tiers.
 */
export var CommandPermissionLevel;
(function (CommandPermissionLevel) {
    CommandPermissionLevel[CommandPermissionLevel["Any"] = 0] = "Any";
    CommandPermissionLevel[CommandPermissionLevel["Normal"] = 0] = "Normal";
    CommandPermissionLevel[CommandPermissionLevel["GameDirectors"] = 1] = "GameDirectors";
    CommandPermissionLevel[CommandPermissionLevel["Operator"] = 1] = "Operator";
    CommandPermissionLevel[CommandPermissionLevel["Admin"] = 2] = "Admin";
    CommandPermissionLevel[CommandPermissionLevel["Host"] = 3] = "Host";
    CommandPermissionLevel[CommandPermissionLevel["Owner"] = 4] = "Owner";
})(CommandPermissionLevel || (CommandPermissionLevel = {}));
/**
 * Execution source origin types.
 */
export var CustomCommandSource;
(function (CustomCommandSource) {
    CustomCommandSource["Block"] = "Block";
    CustomCommandSource["Entity"] = "Entity";
    CustomCommandSource["NPCDialogue"] = "NPCDialogue";
    CustomCommandSource["Server"] = "Server";
})(CustomCommandSource || (CustomCommandSource = {}));
/**
 * Custom command execution status outcome.
 */
export var CustomCommandStatus;
(function (CustomCommandStatus) {
    CustomCommandStatus[CustomCommandStatus["Success"] = 0] = "Success";
    CustomCommandStatus[CustomCommandStatus["Failure"] = 1] = "Failure";
})(CustomCommandStatus || (CustomCommandStatus = {}));
