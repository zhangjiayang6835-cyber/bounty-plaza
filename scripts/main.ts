import { world, system, EntitySpawnAfterEvent } from "@minecraft/server";
import { BossGolemController } from "./boss_golem/index.js";

const activeBosses = new Map<string, BossGolemController>();

/**
 * Handles new entity spawn events to attach controllers to spawned boss golems.
 *
 * @param event Entity spawn event data emitted after world insertion.
 */
export function handleEntitySpawn(event: EntitySpawnAfterEvent): void {
  const entity = event.entity;
  if (entity.typeId === "custom:boss_golem") {
    activeBosses.set(entity.id, new BossGolemController(entity));
  }
}

/**
 * Initializes runtime listeners and periodic watchdog safety loops.
 */
export function initializeExtension(): void {
  world.afterEvents.entitySpawn.subscribe(handleEntitySpawn);

  system.runInterval(() => {
    for (const [id, controller] of activeBosses.entries()) {
      if (controller.getState() === 0) {
        continue;
      }
    }
  }, 20);
}

initializeExtension();
