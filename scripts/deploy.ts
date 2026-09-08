/**
 * Minecraft Bedrock development packs path resolver for automated addon builds.
 * Supports Windows 10/11 retail Store, Xbox App, legacy UWP, Beta/Preview,
 * and standalone launcher installations without requiring administrative privileges.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

/** Supported development pack types. */
export type PackType = 'behavior' | 'resource' | 'skin';

/** Configuration options for path resolution and environment mocking. */
export interface DevPacksOptions {
  packType?: PackType;
  localAppData?: string;
  appData?: string;
  userProfile?: string;
  customEnv?: Record<string, string | undefined>;
  autoCreate?: boolean;
}

/** Directory names corresponding to pack types. */
export const PACK_DIRECTORY_MAP: Record<PackType, string> = {
  behavior: 'development_behavior_packs',
  resource: 'development_resource_packs',
  skin: 'development_skin_packs',
};

/** Well-known package family names for Bedrock installations in order of priority. */
export const KNOWN_BEDROCK_PACKAGES: readonly string[] = [
  'Microsoft.MinecraftWindows_8wekyb3d8bbwe',
  'Microsoft.MinecraftUWP_8wekyb3d8bbwe',
  'Minecraft.Windows_8wekyb3d8bbwe',
  'Microsoft.MinecraftWindowsBeta_8wekyb3d8bbwe',
  'Microsoft.MinecraftBetaUWP_8wekyb3d8bbwe',
  'Microsoft.MinecraftEducationEdition_8wekyb3d8bbwe',
];

/**
 * Discovers the active Minecraft package directory in AppData/Local/Packages.
 *
 * @param packagesDir - The AppData/Local/Packages directory path.
 * @returns The matching package directory path, or null if not found.
 */
export function findMinecraftPackageDir(packagesDir: string): string | null {
  if (!fs.existsSync(packagesDir)) {
    return null;
  }

  for (const knownName of KNOWN_BEDROCK_PACKAGES) {
    const candidate = path.join(packagesDir, knownName);
    const mojangCheck = path.join(candidate, 'LocalState', 'games', 'com.mojang');
    if (fs.existsSync(mojangCheck) || fs.existsSync(candidate)) {
      return candidate;
    }
  }

  try {
    const entries = fs.readdirSync(packagesDir, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory()) {
        continue;
      }
      const lowerName = entry.name.toLowerCase();
      if (lowerName.includes('minecraft') && (lowerName.startsWith('microsoft.') || lowerName.startsWith('minecraft.'))) {
        const fullPath = path.join(packagesDir, entry.name);
        const mojangCheck = path.join(fullPath, 'LocalState', 'games', 'com.mojang');
        if (fs.existsSync(mojangCheck)) {
          return fullPath;
        }
      }
    }
  } catch {
    return null;
  }

  return null;
}

/**
 * Builds an ordered list of candidate paths to the com.mojang base directory.
 *
 * @param options - Environment and directory overrides.
 * @returns An array of candidate paths to inspect.
 */
export function listCandidateMojangPaths(options?: DevPacksOptions): string[] {
  const env = options?.customEnv || process.env;
  const candidates: string[] = [];

  const directPath = env.MINECRAFT_BEDROCK_PATH;
  if (directPath) {
    if (directPath.endsWith('com.mojang')) {
      candidates.push(directPath);
    } else {
      candidates.push(path.join(directPath, 'games', 'com.mojang'));
      candidates.push(path.join(directPath, 'LocalState', 'games', 'com.mojang'));
      candidates.push(directPath);
    }
  }

  const localAppData =
    options?.localAppData ||
    env.LOCALAPPDATA ||
    (options?.userProfile || env.USERPROFILE
      ? path.join(options?.userProfile || env.USERPROFILE || '', 'AppData', 'Local')
      : path.join(os.homedir(), 'AppData', 'Local'));

  const packagesDir = path.join(localAppData, 'Packages');

  const discoveredPkg = findMinecraftPackageDir(packagesDir);
  if (discoveredPkg) {
    candidates.push(path.join(discoveredPkg, 'LocalState', 'games', 'com.mojang'));
  }

  for (const pkgName of KNOWN_BEDROCK_PACKAGES) {
    const pkgPath = path.join(packagesDir, pkgName, 'LocalState', 'games', 'com.mojang');
    if (!candidates.includes(pkgPath)) {
      candidates.push(pkgPath);
    }
  }

  const appData =
    options?.appData ||
    env.APPDATA ||
    (options?.userProfile || env.USERPROFILE
      ? path.join(options?.userProfile || env.USERPROFILE || '', 'AppData', 'Roaming')
      : path.join(os.homedir(), 'AppData', 'Roaming'));

  candidates.push(path.join(localAppData, 'Minecraft', 'LocalState', 'games', 'com.mojang'));
  candidates.push(path.join(localAppData, 'Minecraft Bedrock', 'LocalState', 'games', 'com.mojang'));
  candidates.push(path.join(localAppData, 'Minecraft', 'games', 'com.mojang'));
  candidates.push(path.join(appData, 'Minecraft Bedrock', 'games', 'com.mojang'));

  return candidates;
}

/**
 * Resolves the com.mojang directory for Minecraft Bedrock.
 *
 * @param options - Configuration and mock environment options.
 * @returns The resolved absolute path to com.mojang.
 * @throws Error if com.mojang cannot be located.
 */
export function getMojangBasePath(options?: DevPacksOptions): string {
  const candidates = listCandidateMojangPaths(options);

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  const primaryCandidate = candidates[0] || 'unknown';
  throw new Error(
    `ENOENT: no such file or directory, scandir '${primaryCandidate}'\n` +
      `Failed to locate active Minecraft Bedrock directory across ${candidates.length} candidates:\n` +
      candidates.map((p) => `  - ${p}`).join('\n')
  );
}

/**
 * Resolves the active Minecraft Bedrock development packs directory.
 * Automatically creates the target directory if com.mojang exists but the pack directory is absent.
 *
 * @param optionsOrType - Resolution options or pack type identifier.
 * @returns The absolute path to the development pack directory.
 */
export function getDevelopmentPacksPath(optionsOrType?: DevPacksOptions | PackType): string {
  const options: DevPacksOptions =
    typeof optionsOrType === 'string'
      ? { packType: optionsOrType }
      : optionsOrType || {};

  const env = options.customEnv || process.env;

  if (env.MINECRAFT_DEV_PACKS_PATH && fs.existsSync(env.MINECRAFT_DEV_PACKS_PATH)) {
    return env.MINECRAFT_DEV_PACKS_PATH;
  }

  const packType = options.packType || 'behavior';
  const folderName = PACK_DIRECTORY_MAP[packType] || PACK_DIRECTORY_MAP.behavior;
  const mojangBase = getMojangBasePath(options);
  const targetPath = path.join(mojangBase, folderName);

  if (!fs.existsSync(targetPath)) {
    if (options.autoCreate !== false) {
      fs.mkdirSync(targetPath, { recursive: true });
    } else {
      throw new Error(`ENOENT: no such file or directory, scandir '${targetPath}'`);
    }
  }

  return targetPath;
}

/**
 * Alias for getDevelopmentPacksPath matching legacy build script naming.
 *
 * @param options - Resolution options.
 * @returns The absolute path to the resolved development packs directory.
 */
export function resolveDevPacks(options?: DevPacksOptions): string {
  return getDevelopmentPacksPath(options);
}
