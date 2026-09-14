import { Player } from "@minecraft/server";
import { truncateInventoryItemName, getInventorySlotDisplayName } from "./inventory_utils.js";

export { truncateInventoryItemName, getInventorySlotDisplayName };

/**
 * Updates the inventory projection for a player.
 *
 * @param player Target player entity.
 * @returns The projected 16-character inventory text slice for the selected hotbar slot.
 */
export declare function updatePlayerInventoryProjection(player: Player): string;

/**
 * Initializes the periodic inventory projection HUD update loop across all players.
 *
 * @returns The timer identifier returned by the Bedrock system scheduler.
 */
export declare function initializeInventoryHudProjection(): number;
