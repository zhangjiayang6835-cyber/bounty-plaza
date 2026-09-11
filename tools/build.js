import * as fs from 'node:fs';
import * as path from 'node:path';
import { deploy } from '../scripts/deploy.js';
import { syncDirectory, resolveMojangDevelopmentPath } from './sync.js';

/**
 * Builds and stages pack files.
 *
 * @param {object} [options={}] - Build options.
 * @returns {object} Build stats.
 */
export function runBuild(options = {}) {
  const sourceDir = path.resolve(options.sourceDir || 'packs/behavior_pack');
  const destDir = options.destDir
    ? path.resolve(options.destDir)
    : options.deploy
    ? resolveMojangDevelopmentPath('', 'behavior')
    : path.resolve('dist/behavior_pack');

  if (!fs.existsSync(sourceDir)) {
    throw new Error(`Source directory not found: ${sourceDir}`);
  }

  const syncStats = syncDirectory(sourceDir, destDir, { clean: true });
  return {
    success: true,
    stats: {
      source: sourceDir,
      dest: destDir,
      copied: syncStats.copied,
      removed: syncStats.removed
    }
  };
}

/**
 * CLI execution entrypoint for build and deploy script.
 */
export function main() {
  const args = process.argv.slice(2);
  const isDeploy = args.includes('--deploy');

  if (isDeploy) {
    const res = deploy({
      packType: 'behavior'
    });
    console.log(`[Build] Deployed to ${res.destination}`);
    return;
  }

  const res = runBuild();
  console.log(`[Build] Built pack to ${res.stats.dest}`);
}

if (process.argv[1] && process.argv[1].endsWith('build.js')) {
  main();
}
