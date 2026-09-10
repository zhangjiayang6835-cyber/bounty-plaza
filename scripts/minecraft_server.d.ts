/**
 * Ambient type declarations for Bedrock Script API module @minecraft/server.
 */

declare module "@minecraft/server" {
  export interface System {
    runInterval(callback: () => void, tickInterval?: number): number;
    clearRun(runId: number): void;
  }

  export interface Player {
    id: string;
    name: string;
  }

  export interface World {
    getAllPlayers(): Player[];
  }

  export const system: System;
  export const world: World;
}
