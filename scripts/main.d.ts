import { EntitySpawnAfterEvent } from "@minecraft/server";
/**
 * Handles new entity spawn events to attach controllers to spawned boss golems.
 *
 * @param event Entity spawn event data emitted after world insertion.
 */
export declare function handleEntitySpawn(event: EntitySpawnAfterEvent): void;
/**
 * Initializes runtime listeners and periodic watchdog safety loops.
 */
export declare function initializeExtension(): void;
