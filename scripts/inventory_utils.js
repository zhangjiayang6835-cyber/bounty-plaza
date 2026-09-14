/**
 * Truncates an inventory item name to a maximum of 16 characters for HUD display.
 *
 * @param {string} rawName Raw item name or identifier.
 * @returns {string} Truncated string with a maximum length of 16 characters.
 */
export function truncateInventoryItemName(rawName) {
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
 * @param {{ typeId: string, nameTag?: string }} [item] An item representation containing optional nameTag and typeId.
 * @returns {string} The formatted and truncated 16-character item name.
 */
export function getInventorySlotDisplayName(item) {
    if (!item) {
        return "";
    }
    const displayName = item.nameTag && item.nameTag.trim().length > 0
        ? item.nameTag
        : item.typeId;
    return truncateInventoryItemName(displayName);
}
