import * as fs from 'node:fs';
import * as path from 'node:path';
import { resolveBedrockDevPath, syncDirectory as syncDir } from '../scripts/deploy.js';

/**
 * Resolves Bedrock development directory with modern Windows roaming paths and graceful fallback.
 *
 * @param {string} [customDestination=''] - Explicit path override.
 * @param {string} [packType='behavior'] - Target pack type ('behavior' | 'resource').
 * @returns {string} Resolved directory path.
 */
export function resolveMojangDevelopmentPath(customDestination = '', packType = 'behavior') {
  return resolveBedrockDevPath({
    customDestination,
    packType
  });
}

/**
 * Synchronizes directory contents from source to destination.
 *
 * @param {string} sourceDir - Source directory.
 * @param {string} destDir - Destination directory.
 * @param {object} [options={ clean: true }] - Sync options.
 * @returns {{ copied: number, removed: number }} Sync stats.
 */
export function syncDirectory(sourceDir, destDir, options = { clean: true }) {
  return syncDir(sourceDir, destDir, options);
}
