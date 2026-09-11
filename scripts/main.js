import { initializeStartupHooks } from './startup.js';

/**
 * Initializes BDS addon subsystems and event hooks.
 */
export function main() {
  initializeStartupHooks();
}

main();
