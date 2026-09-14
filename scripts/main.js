/**
 * Main script entrypoint for Bedrock Behavior Pack Kinematic Hitbox Manager.
 */
import { KinematicHitboxEngine } from "./hitbox_math/index.js";
export const hitboxEngine = new KinematicHitboxEngine();
let currentWorldTick = 0;
/**
 * Handles per-tick kinematic hitbox updates and continuous collision detection.
 */
export function onKinematicTick() {
    currentWorldTick += 1;
    hitboxEngine.tickKinematics(currentWorldTick);
}
/**
 * Initializes Script API hooks when running in Minecraft Bedrock environment.
 */
export async function initializeScriptHooks() {
    try {
        const serverModule = await import("@minecraft/server");
        if (serverModule && serverModule.system) {
            serverModule.system.runInterval(() => {
                onKinematicTick();
            }, 1);
        }
    }
    catch {
        return;
    }
}
initializeScriptHooks();
