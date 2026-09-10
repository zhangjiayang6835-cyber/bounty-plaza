import {
    world,
    system,
    EntityComponentTypes
} from "@minecraft/server";
import {
    truncateInventoryItemName,
    getInventorySlotDisplayName
} from "./inventory_utils.js";

export { truncateInventoryItemName, getInventorySlotDisplayName };

/**
 * Updates the inventory projection for a player.
 *
 * @param {import("@minecraft/server").Player} player Target player entity.
 * @returns {string} The projected 16-character inventory text slice for the selected hotbar slot.
 */
export function updatePlayerInventoryProjection(player) {
    const inventory = player.getComponent(EntityComponentTypes.Inventory);
    if (!inventory || !inventory.container) {
        return "";
    }
    const slotIndex = player.selectedSlotIndex;
    const item = inventory.container.getItem(slotIndex);
    return getInventorySlotDisplayName(item);
}

/**
 * Initializes the periodic inventory projection HUD update loop across all players.
 *
 * @returns {number} The timer identifier returned by the Bedrock system scheduler.
 */
export function initializeInventoryHudProjection() {
    return system.runInterval(() => {
        for (const player of world.getAllPlayers()) {
            updatePlayerInventoryProjection(player);
        }
    }, 4);
}

initializeInventoryHudProjection();
