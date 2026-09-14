import {
    world,
    system,
    Player,
    EntityComponentTypes,
    EntityInventoryComponent
} from "@minecraft/server";
import {
    truncateInventoryItemName,
    getInventorySlotDisplayName
} from "./inventory_utils.js";

export { truncateInventoryItemName, getInventorySlotDisplayName };

/**
 * Updates the inventory projection for a player.
 *
 * @param player Target player entity.
 * @returns The projected 16-character inventory text slice for the selected hotbar slot.
 */
export function updatePlayerInventoryProjection(player: Player): string {
    const inventory = player.getComponent(EntityComponentTypes.Inventory) as EntityInventoryComponent | undefined;
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
 * @returns The timer identifier returned by the Bedrock system scheduler.
 */
export function initializeInventoryHudProjection(): number {
    return system.runInterval(() => {
        for (const player of world.getAllPlayers()) {
            updatePlayerInventoryProjection(player);
        }
    }, 4);
}

initializeInventoryHudProjection();
