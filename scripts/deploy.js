import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';

/**
 * Returns candidate search paths for Minecraft Bedrock on Windows platforms.
 *
 * @param {Record<string, string | undefined>} env - Environment variable map.
 * @param {string} home - User home directory.
 * @param {string} subFolder - Target pack subfolder name.
 * @returns {string[]} Ordered array of candidate directory paths.
 */
export function getWindowsCandidatePaths(env, home, subFolder) {
  const candidates = [];
  const appData = env.APPDATA || path.join(home, 'AppData', 'Roaming');
  const localAppData = env.LOCALAPPDATA || path.join(home, 'AppData', 'Local');

  candidates.push(path.join(appData, '.minecraft', 'bedrock', subFolder));
  candidates.push(path.join(appData, 'Minecraftpe', 'games', 'com.mojang', subFolder));
  candidates.push(path.join(localAppData, 'Minecraftpe', 'games', 'com.mojang', subFolder));

  const knownPackages = [
    'Microsoft.MinecraftUWP_8wekyb3d8bbwe',
    'Microsoft.MinecraftWindows_8wekyb3d8bbwe',
    'Minecraft.Windows_8wekyb3d8bbwe'
  ];

  for (const pkgName of knownPackages) {
    candidates.push(
      path.join(localAppData, 'Packages', pkgName, 'LocalState', 'games', 'com.mojang', subFolder)
    );
  }

  candidates.push(path.join(home, '.minecraft', 'bedrock', subFolder));
  return candidates;
}

/**
 * Resolves the Bedrock development directory with modern Windows 11 roaming support and graceful fallback.
 *
 * @param {object} [options={}] - Path resolution options.
 * @returns {string} Absolute path to target development pack directory.
 */
export function resolveBedrockDevPath(options = {}) {
  if (options.customDestination) {
    return path.resolve(options.customDestination);
  }

  const env = options.env || process.env;
  const currentPlatform = options.platform || process.platform;
  const home = options.homedir || os.homedir();
  const packType = options.packType || 'behavior';
  const subFolder = packType === 'behavior' ? 'development_behavior_packs' : 'development_resource_packs';

  const envOverride = env.MINECRAFT_DEVELOPMENT_PATH || env.BEDROCK_DEVELOPMENT_PATH;
  if (envOverride) {
    return path.resolve(envOverride, subFolder);
  }

  let candidates = [];

  if (currentPlatform === 'win32') {
    candidates = getWindowsCandidatePaths(env, home, subFolder);
  } else if (currentPlatform === 'darwin') {
    candidates = [
      path.join(home, 'Library', 'Application Support', 'mcpelauncher', 'games', 'com.mojang', subFolder),
      path.join(home, 'Library', 'Application Support', 'minecraftpe', 'games', 'com.mojang', subFolder)
    ];
  } else {
    candidates = [
      path.join(home, '.local', 'share', 'mcpelauncher', 'games', 'com.mojang', subFolder),
      path.join(home, '.local', 'share', 'minecraftpe', 'games', 'com.mojang', subFolder),
      path.join(home, '.var', 'app', 'io.mrarm.mcpelauncher', 'data', 'mcpelauncher', 'games', 'com.mojang', subFolder)
    ];
  }

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
    const parentDir = path.dirname(candidate);
    if (fs.existsSync(parentDir)) {
      return candidate;
    }
  }

  if (candidates.length > 0) {
    return candidates[0];
  }

  const localDist = options.localDistRoot || 'dist';
  return path.resolve(localDist, packType === 'behavior' ? 'behavior_pack' : 'resource_pack');
}

/**
 * Backward-compatible alias for resolveBedrockDevPath.
 *
 * @param {string} [customDestination=''] - Explicit override path.
 * @param {string} [packType='behavior'] - Target pack type ('behavior' | 'resource').
 * @param {object} [options={}] - Additional resolution options.
 * @returns {string} Absolute directory path.
 */
export function resolveMojangDevelopmentPath(customDestination = '', packType = 'behavior', options = {}) {
  return resolveBedrockDevPath({
    customDestination,
    packType,
    ...options
  });
}

/**
 * Synchronizes contents from source folder to target destination.
 *
 * @param {string} sourceDir - Source directory path.
 * @param {string} destDir - Target directory path.
 * @param {object} [options={}] - Sync configuration options.
 * @returns {{ copied: number, removed: number }} Statistics of copied and removed files.
 */
export function syncDirectory(sourceDir, destDir, options = {}) {
  if (!fs.existsSync(sourceDir)) {
    throw new Error(`Source directory not found: ${sourceDir}`);
  }

  if (!options.dryRun && !fs.existsSync(destDir)) {
    fs.mkdirSync(destDir, { recursive: true });
  }

  let copied = 0;
  let removed = 0;
  const sourceFiles = collectFilesRecursively(sourceDir);
  const sourceRelativeSet = new Set();

  for (const srcFile of sourceFiles) {
    const rel = path.relative(sourceDir, srcFile);
    sourceRelativeSet.add(rel);
    const targetFile = path.join(destDir, rel);

    let needsCopy = true;
    if (fs.existsSync(targetFile)) {
      const srcStat = fs.statSync(srcFile);
      const targetStat = fs.statSync(targetFile);
      if (srcStat.size === targetStat.size) {
        const srcBuf = fs.readFileSync(srcFile);
        const targetBuf = fs.readFileSync(targetFile);
        if (srcBuf.equals(targetBuf)) {
          needsCopy = false;
        }
      }
    }

    if (needsCopy) {
      if (!options.dryRun) {
        fs.mkdirSync(path.dirname(targetFile), { recursive: true });
        fs.copyFileSync(srcFile, targetFile);
      }
      copied++;
    }
  }

  if (options.clean !== false && fs.existsSync(destDir)) {
    const destFiles = collectFilesRecursively(destDir);
    for (const dFile of destFiles) {
      const rel = path.relative(destDir, dFile);
      if (!sourceRelativeSet.has(rel)) {
        if (!options.dryRun) {
          fs.unlinkSync(dFile);
        }
        removed++;
      }
    }
    if (!options.dryRun) {
      pruneEmptyDirectories(destDir);
    }
  }

  return { copied, removed };
}

/**
 * Deploys Bedrock pack to target development folder with graceful fallback.
 *
 * @param {object} [options={}] - Deployment execution parameters.
 * @returns {object} Execution report.
 */
export function deploy(options = {}) {
  const warnings = [];
  const currentPlatform = options.platform || process.platform;
  const packType = options.packType || 'behavior';
  let targetPath = resolveBedrockDevPath(options);
  let fallbackUsed = false;

  try {
    const stat = fs.statSync(targetPath);
    if (!stat.isDirectory()) {
      warnings.push(`Target ${targetPath} is not a directory. Falling back to local output.`);
      fallbackUsed = true;
      targetPath = path.resolve(options.localDistRoot || 'dist', packType === 'behavior' ? 'behavior_pack' : 'resource_pack');
    }
  } catch (err) {
    if (err && err.code === 'ENOENT') {
      warnings.push(`Target directory ${targetPath} not found.`);
      if (options.autoCreate !== false) {
        try {
          fs.mkdirSync(targetPath, { recursive: true });
        } catch (createErr) {
          warnings.push(`Failed to auto-create ${targetPath}: ${createErr.message}. Falling back to local dist.`);
          fallbackUsed = true;
          targetPath = path.resolve(options.localDistRoot || 'dist', packType === 'behavior' ? 'behavior_pack' : 'resource_pack');
          fs.mkdirSync(targetPath, { recursive: true });
        }
      } else {
        fallbackUsed = true;
        targetPath = path.resolve(options.localDistRoot || 'dist', packType === 'behavior' ? 'behavior_pack' : 'resource_pack');
        fs.mkdirSync(targetPath, { recursive: true });
      }
    } else {
      warnings.push(`Filesystem stat error on ${targetPath}: ${err.message}. Falling back to local dist.`);
      fallbackUsed = true;
      targetPath = path.resolve(options.localDistRoot || 'dist', packType === 'behavior' ? 'behavior_pack' : 'resource_pack');
      fs.mkdirSync(targetPath, { recursive: true });
    }
  }

  let sourceDir = options.sourceDir;
  if (!sourceDir) {
    const candidates = [
      path.resolve('packs', packType === 'behavior' ? 'behavior_pack' : 'resource_pack'),
      path.resolve('dist', packType === 'behavior' ? 'behavior_pack' : 'resource_pack'),
      path.resolve('_temp', packType === 'behavior' ? 'behavior_pack' : 'resource_pack'),
      path.resolve('.')
    ];
    for (const c of candidates) {
      if (fs.existsSync(c) && (fs.existsSync(path.join(c, 'manifest.json')) || c === path.resolve('.'))) {
        sourceDir = c;
        break;
      }
    }
  }

  if (!sourceDir || !fs.existsSync(sourceDir)) {
    throw new Error(`Source directory not found for deployment: ${sourceDir}`);
  }

  const syncStats = syncDirectory(sourceDir, targetPath, {
    clean: options.clean !== false,
    dryRun: options.dryRun || false
  });

  return {
    success: true,
    destination: targetPath,
    source: sourceDir,
    copiedCount: syncStats.copied,
    removedCount: syncStats.removed,
    fallbackUsed,
    platform: currentPlatform,
    warnings
  };
}

/**
 * Traverses a folder recursively to collect all file paths.
 *
 * @param {string} dir - Root directory.
 * @returns {string[]} Flat array of absolute file paths.
 */
function collectFilesRecursively(dir) {
  const result = [];
  if (!fs.existsSync(dir)) {
    return result;
  }
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      result.push(...collectFilesRecursively(full));
    } else if (entry.isFile()) {
      result.push(full);
    }
  }
  return result;
}

/**
 * Recursively cleans empty subdirectories within target folder.
 *
 * @param {string} dir - Directory to inspect and prune.
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

/**
 * Main execution handler when run via CLI.
 */
export function main() {
  const args = process.argv.slice(2);
  let customDest;
  const destIndex = args.indexOf('--dest');
  if (destIndex !== -1 && args[destIndex + 1]) {
    customDest = args[destIndex + 1];
  }

  const dryRun = args.includes('--dry-run');
  const packType = args.includes('--resource') ? 'resource' : 'behavior';

  try {
    const result = deploy({
      customDestination: customDest,
      dryRun,
      packType
    });
    console.log(`[Deploy] Success: Synced ${result.copiedCount} files to ${result.destination}`);
    if (result.fallbackUsed) {
      console.warn('[Deploy] Warning: Fallback path was utilized during deployment.');
    }
    for (const w of result.warnings) {
      console.warn(`[Deploy] Warning: ${w}`);
    }
  } catch (err) {
    console.error(`[Deploy][Fatal] ${err.message}`);
    process.exit(1);
  }
}

if (process.argv[1] && process.argv[1].includes('deploy')) {
  main();
}
