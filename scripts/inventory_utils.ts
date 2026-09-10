/**
 * Truncates an inventory item name to a maximum of 16 characters for HUD display.
 *
 * @param rawName Raw item name or identifier.
 * @returns Truncated string with a maximum length of 16 characters.
 */
export function truncateInventoryItemName(rawName: string): string {
    if (!rawName) {
        return "";
    }
    const cleanName = rawName.replace(/^minecraft:/, "");
    if (cleanName.length <= 16) {
        return cleanName;
    }
    return cleanName.slice(0, 16);
}

/**
 * Resolves the display name for an item in an inventory container slot.
 *
 * @param item An item representation containing optional nameTag and typeId.
 * @returns The formatted and truncated 16-character item name.
 */
export function getInventorySlotDisplayName(item?: { typeId: string; nameTag?: string }): string {
    if (!item) {
        return "";
    }
    const displayName = item.nameTag && item.nameTag.trim().length > 0
        ? item.nameTag
        : item.typeId;
    return truncateInventoryItemName(displayName);
}
