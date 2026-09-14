/**
 * Truncates an inventory item name to a maximum of 16 characters for HUD display.
 *
 * @param rawName Raw item name or identifier.
 * @returns Truncated string with a maximum length of 16 characters.
 */
export declare function truncateInventoryItemName(rawName: string): string;

/**
 * Resolves the display name for an item in an inventory container slot.
 *
 * @param item An item representation containing optional nameTag and typeId.
 * @returns The formatted and truncated 16-character item name.
 */
export declare function getInventorySlotDisplayName(item?: {
    typeId: string;
    nameTag?: string;
}): string;
