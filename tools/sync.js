import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

/**
 * Resolves the com.mojang development directory or falls back to a local build directory.
 *
 * @param {string} [customDestination] - Explicit target directory override.
 * @param {string} [packType='behavior'] - Pack type: 'behavior' or 'resource'.
 * @returns {string} Target development directory path.
 */
export function resolveMojangDevelopmentPath(customDestination = '', packType = 'behavior') {
  if (customDestination) {
    return path.resolve(customDestination);
  }

  const subFolder = packType === 'behavior' ? 'development_behavior_packs' : 'development_resource_packs';

  if (process.env.MINECRAFT_DEVELOPMENT_PATH) {
    return path.join(process.env.MINECRAFT_DEVELOPMENT_PATH, subFolder);
  }

  const localAppData = process.env.LOCALAPPDATA;
  if (localAppData) {
    const packagesDir = path.join(localAppData, 'Packages');
    const knownPackages = [
      'Microsoft.MinecraftUWP_8wekyb3d8bbwe',
      'Microsoft.MinecraftWindows_8wekyb3d8bbwe',
      'Minecraft.Windows_8wekyb3d8bbwe',
    ];

    for (const pkgName of knownPackages) {
      const candidate = path.join(packagesDir, pkgName, 'LocalState', 'games', 'com.mojang', subFolder);
      if (fs.existsSync(path.dirname(candidate))) {
        return candidate;
      }
    }
  }

  return path.resolve('dist', packType === 'behavior' ? 'behavior_pack' : 'resource_pack');
}

/**
 * Recursively synchronizes files from source directory to target directory.
 *
 * @param {string} sourceDir - Source directory containing staged files.
 * @param {string} destDir - Destination directory to synchronize into.
 * @param {object} [options] - Synchronization options.
 * @param {boolean} [options.clean=true] - If true, removes files in destination that do not exist in source.
 * @returns {{ copied: number, removed: number }} Statistics on synchronized files.
 */
export function syncDirectory(sourceDir, destDir, options = { clean: true }) {
  if (!fs.existsSync(sourceDir)) {
    throw new Error(`Source directory does not exist: ${sourceDir}`);
  }

  fs.mkdirSync(destDir, { recursive: true });

  let copied = 0;
  let removed = 0;

  const sourceFiles = collectAllFiles(sourceDir);
  const sourceRelativeSet = new Set();

  for (const srcFile of sourceFiles) {
    const rel = path.relative(sourceDir, srcFile);
    sourceRelativeSet.add(rel);
    const targetFile = path.join(destDir, rel);

    fs.mkdirSync(path.dirname(targetFile), { recursive: true });

    let needsCopy = true;
    if (fs.existsSync(targetFile)) {
      const srcStat = fs.statSync(srcFile);
      const targetStat = fs.statSync(targetFile);
      if (srcStat.size === targetStat.size) {
        const srcBuffer = fs.readFileSync(srcFile);
        const targetBuffer = fs.readFileSync(targetFile);
        if (srcBuffer.equals(targetBuffer)) {
          needsCopy = false;
        }
      }
    }

    if (needsCopy) {
      fs.copyFileSync(srcFile, targetFile);
      copied++;
    }
  }

  if (options.clean && fs.existsSync(destDir)) {
    const destFiles = collectAllFiles(destDir);
    for (const dFile of destFiles) {
      const rel = path.relative(destDir, dFile);
      if (!sourceRelativeSet.has(rel)) {
        fs.unlinkSync(dFile);
        removed++;
      }
    }
    pruneEmptyDirectories(destDir);
  }

  return { copied, removed };
}

/**
 * Recursively collects all file paths within a directory.
 *
 * @param {string} dir - Directory to scan.
 * @returns {string[]} Flat list of file paths.
 */
function collectAllFiles(dir) {
  const list = [];
  if (!fs.existsSync(dir)) {
    return list;
  }
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      list.push(...collectAllFiles(full));
    } else if (entry.isFile()) {
      list.push(full);
    }
  }
  return list;
}

/**
 * Recursively prunes empty subdirectories within a directory tree.
 *
 * @param {string} dir - Directory to clean up.
 */
function pruneEmptyDirectories(dir) {
  if (!fs.existsSync(dir)) {
    return;
  }
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isDirectory()) {
      const full = path.join(dir, entry.name);
      pruneEmptyDirectories(full);
    }
  }
  const remaining = fs.readdirSync(dir);
  if (remaining.length === 0) {
    try {
      fs.rmdirSync(dir);
    } catch {}
  }
}
