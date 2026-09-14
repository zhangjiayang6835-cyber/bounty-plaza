import { initializeStartupHooks } from './startup.js';

/**
 * Main behavior pack entrypoint initializing system hooks.
 */
export function initializeMain(): void {
  initializeStartupHooks();
}

initializeMain();
