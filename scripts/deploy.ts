// scripts/deploy.ts
import path from 'path';
import fs from 'fs';
import os from 'os';

/**
 * Returns the path to the Minecraft development behavior packs directory.
 * Handles different installation types (UWP, preview, new launcher).
 */
export function getDevelopmentPacksPath(): string {
  const localAppData = process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local');
  
  // Potential paths where Minecraft Bedrock could be installed
  const possiblePaths = [
    // Standard Bedrock (Microsoft Store)
    path.join(localAppData, 'Packages', 'Microsoft.MinecraftUWP_8wekyb3d8bbwe', 'LocalState', 'games', 'com.mojang', 'development_behavior_packs'),
    // Minecraft Preview
    path.join(localAppData, 'Packages', 'Microsoft.MinecraftWindowsBeta_8wekyb3d8bbwe', 'LocalState', 'games', 'com.mojang', 'development_behavior_packs'),
    // New Minecraft Launcher / Game Pass PC (Sometimes installs here)
    path.join(localAppData, 'Packages', 'Microsoft.4297127D64EC6_8wekyb3d8bbwe', 'LocalState', 'games', 'com.mojang', 'development_behavior_packs')
  ];

  for (const packPath of possiblePaths) {
    if (fs.existsSync(packPath)) {
      return packPath;
    }
  }
  
  // If we couldn't find it but the com.mojang folder exists, let's try creating the development_behavior_packs folder.
  // Sometimes the game is installed but hasn't created the dev folders yet.
  const mojangPaths = [
      path.join(localAppData, 'Packages', 'Microsoft.MinecraftUWP_8wekyb3d8bbwe', 'LocalState', 'games', 'com.mojang'),
      path.join(localAppData, 'Packages', 'Microsoft.MinecraftWindowsBeta_8wekyb3d8bbwe', 'LocalState', 'games', 'com.mojang'),
      path.join(localAppData, 'Packages', 'Microsoft.4297127D64EC6_8wekyb3d8bbwe', 'LocalState', 'games', 'com.mojang')
  ];

  for (const mojangPath of mojangPaths) {
      if (fs.existsSync(mojangPath)) {
          const newPackPath = path.join(mojangPath, 'development_behavior_packs');
          try {
              fs.mkdirSync(newPackPath, { recursive: true });
              return newPackPath;
          } catch (e) {
              console.warn(`Could not create directory ${newPackPath}:`, e);
          }
      }
  }

  throw new Error(`ENOENT: no such file or directory. Could not locate Minecraft Bedrock 'com.mojang' folder in expected AppData\\Local\\Packages directories. Is the game installed and has it been launched at least once?`);
}

// Unit Tests Simulation (for validation)
export function runMockTests() {
  console.log("Running simulated unit tests...");
  const oldLocalAppData = process.env.LOCALAPPDATA;
  
  // Test 1: Fallback error
  process.env.LOCALAPPDATA = '/tmp/mock_appdata_none';
  try {
      getDevelopmentPacksPath();
      console.error("Test 1 Failed: Should have thrown an error");
  } catch (e) {
      console.log("Test 1 Passed: Error thrown correctly when no path exists");
  }

  // Test 2: Standard UWP
  process.env.LOCALAPPDATA = '/tmp/mock_appdata_uwp';
  const uwpPath = path.join('/tmp/mock_appdata_uwp', 'Packages', 'Microsoft.MinecraftUWP_8wekyb3d8bbwe', 'LocalState', 'games', 'com.mojang', 'development_behavior_packs');
  fs.mkdirSync(uwpPath, {recursive: true});
  const res1 = getDevelopmentPacksPath();
  if (res1 === uwpPath) {
      console.log("Test 2 Passed: Found standard UWP path");
  } else {
      console.error(`Test 2 Failed: Expected ${uwpPath}, got ${res1}`);
  }

  // Test 3: Missing dev folder but mojang exists
  process.env.LOCALAPPDATA = '/tmp/mock_appdata_mojang';
  const mojangPath = path.join('/tmp/mock_appdata_mojang', 'Packages', 'Microsoft.4297127D64EC6_8wekyb3d8bbwe', 'LocalState', 'games', 'com.mojang');
  fs.mkdirSync(mojangPath, {recursive: true});
  const res2 = getDevelopmentPacksPath();
  const expectedNewPath = path.join(mojangPath, 'development_behavior_packs');
  if (res2 === expectedNewPath && fs.existsSync(expectedNewPath)) {
      console.log("Test 3 Passed: Created missing development_behavior_packs folder");
  } else {
      console.error("Test 3 Failed: Did not properly create or find path");
  }

  // Cleanup
  process.env.LOCALAPPDATA = oldLocalAppData;
}

// If run directly, run tests
if (require.main === module) {
    runMockTests();
}
