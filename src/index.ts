/**
 * TG Station TypeScript - Main entry point
 * 
 * This is the main entry point for the transpiled TG Station codebase.
 * It initializes the game engine and starts the game loop.
 */

import { GameEngine } from './engine/GameEngine';
import { Logger } from './utils/Logger';

const logger = new Logger('Main');

// Initialize the game engine
const engine = new GameEngine();

// Start the game
try {
  engine.initialize();
  engine.start();
  logger.info('TG Station TypeScript started successfully');
} catch (error) {
  logger.error('Failed to start TG Station TypeScript', error);
  process.exit(1);
}