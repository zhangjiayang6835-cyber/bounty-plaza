/**
 * Type definitions for TG Station TypeScript
 * 
 * This file contains all the type definitions used throughout the codebase.
 */

// Basic game object types
export interface GameObject {
  id: string;
  name: string;
  type: string;
  x: number;
  y: number;
  z: number;
}

// Mobile entity types
export interface Mob extends GameObject {
  health: number;
  maxHealth: number;
  stamina: number;
  maxStamina: number;
  consciousness: number;
}

// Area types
export interface Area extends GameObject {
  contents: GameObject[];
}

// Game mode types
export interface GameMode {
  name: string;
  description: string;
  initialize(): void;
  setup(): void;
  tick(): void;
}

// Item types
export interface Item extends GameObject {
  amount?: number;
  flags: string[];
}

// Component types
export interface Component {
  parent: GameObject;
  initialize(): void;
  update(): void;
  destroy(): void;
}

// System types
export interface System {
  initialize(): void;
  update(): void;
  shutdown(): void;
}