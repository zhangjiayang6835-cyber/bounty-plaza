/**
 * Ambient type definitions for @minecraft/server Script API.
 */

declare module "@minecraft/server" {
  export interface System {
    runInterval(callback: () => void, interval?: number): number;
    clearRun(runId: number): void;
  }

  export const system: System;
}
