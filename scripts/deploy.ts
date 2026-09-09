/**
 * scripts/deploy.ts
 * Solves: [Bounty: $450] Deploy Script Fails with ENOENT on Windows 11
 */

import path from 'path';
import fs from 'fs';

export const KNOWN_PACK_PACKAGE_NAMES = [
  'Microsoft.MinecraftWindows_8wekyb3d8bbwe', // Modern retail GDK / Windows 11
  'Microsoft.MinecraftUWP_8wekyb3d8bbwe',     // Legacy Store UWP
  'Microsoft.MinecraftWindowsBeta_8wekyb3d8bbwe' // Preview / Beta build
];

export function getDevelopmentPacksPath(customRoot?: string): string {
  const envOverride = process.env.MINECRAFT_DEV_PACKS_PATH || process.env.BEDROCK_PACKS_PATH;
  if (envOverride && fs.existsSync(envOverride)) {
    return envOverride;
  }

  const localAppData = customRoot || process.env.LOCALAPPDATA || '';
  const packagesDir = path.join(localAppData, 'Packages');

  let selectedMojangRoot: string | null = null;

  for (const pkgName of KNOWN_PACK_PACKAGE_NAMES) {
    const candidateMojang = path.join(packagesDir, pkgName, 'LocalState', 'games', 'com.mojang');
    if (fs.existsSync(candidateMojang)) {
      selectedMojangRoot = candidateMojang;
      break;
    }
  }

  if (!selectedMojangRoot && fs.existsSync(packagesDir)) {
    selectedMojangRoot = path.join(packagesDir, KNOWN_PACK_PACKAGE_NAMES[0], 'LocalState', 'games', 'com.mojang');
  }

  if (!selectedMojangRoot) {
    throw new Error('Could not locate or resolve Minecraft Bedrock data directory on this Windows environment.');
  }

  const devPacksPath = path.join(selectedMojangRoot, 'development_behavior_packs');

  if (!fs.existsSync(devPacksPath)) {
    fs.mkdirSync(devPacksPath, { recursive: true });
  }

  return devPacksPath;
}
