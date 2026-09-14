import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import {
  findMinecraftPackageDir,
  getDevelopmentPacksPath,
  resolveDevPacks,
} from './deploy';

/**
 * Creates an isolated temporary directory for testing.
 *
 * @returns Path to temporary directory.
 */
function createSandbox(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'bedrock-deploy-test-'));
}

/**
 * Recursively removes temporary sandbox directory.
 *
 * @param sandbox - Sandbox path to delete.
 */
function cleanSandbox(sandbox: string): void {
  if (fs.existsSync(sandbox)) {
    fs.rmSync(sandbox, { recursive: true, force: true });
  }
}

/**
 * Test legacy UWP package directory resolution.
 */
function testLegacyUwpResolution(): void {
  const sandbox = createSandbox();
  try {
    const localAppData = path.join(sandbox, 'AppData', 'Local');
    const mojangDir = path.join(
      localAppData,
      'Packages',
      'Microsoft.MinecraftUWP_8wekyb3d8bbwe',
      'LocalState',
      'games',
      'com.mojang'
    );
    const expectedPacks = path.join(mojangDir, 'development_behavior_packs');
    fs.mkdirSync(expectedPacks, { recursive: true });

    const resolved = getDevelopmentPacksPath({ localAppData });
    assert.strictEqual(resolved, expectedPacks);
  } finally {
    cleanSandbox(sandbox);
  }
}

/**
 * Test modern retail Windows Store package detection.
 */
function testModernWindowsResolution(): void {
  const sandbox = createSandbox();
  try {
    const localAppData = path.join(sandbox, 'AppData', 'Local');
    const mojangDir = path.join(
      localAppData,
      'Packages',
      'Microsoft.MinecraftWindows_8wekyb3d8bbwe',
      'LocalState',
      'games',
      'com.mojang'
    );
    const expectedPacks = path.join(mojangDir, 'development_behavior_packs');
    fs.mkdirSync(expectedPacks, { recursive: true });

    const resolved = getDevelopmentPacksPath({ localAppData });
    assert.strictEqual(resolved, expectedPacks);
  } finally {
    cleanSandbox(sandbox);
  }
}

/**
 * Test Windows App Installer package detection.
 */
function testMapiResolution(): void {
  const sandbox = createSandbox();
  try {
    const localAppData = path.join(sandbox, 'AppData', 'Local');
    const mojangDir = path.join(
      localAppData,
      'Packages',
      'Minecraft.Windows_8wekyb3d8bbwe',
      'LocalState',
      'games',
      'com.mojang'
    );
    const expectedPacks = path.join(mojangDir, 'development_behavior_packs');
    fs.mkdirSync(expectedPacks, { recursive: true });

    const resolved = getDevelopmentPacksPath({ localAppData });
    assert.strictEqual(resolved, expectedPacks);
  } finally {
    cleanSandbox(sandbox);
  }
}

/**
 * Test Bedrock Preview and Beta package detection.
 */
function testBetaResolution(): void {
  const sandbox = createSandbox();
  try {
    const localAppData = path.join(sandbox, 'AppData', 'Local');
    const mojangDir = path.join(
      localAppData,
      'Packages',
      'Microsoft.MinecraftWindowsBeta_8wekyb3d8bbwe',
      'LocalState',
      'games',
      'com.mojang'
    );
    const expectedPacks = path.join(mojangDir, 'development_behavior_packs');
    fs.mkdirSync(expectedPacks, { recursive: true });

    const resolved = getDevelopmentPacksPath({ localAppData });
    assert.strictEqual(resolved, expectedPacks);
  } finally {
    cleanSandbox(sandbox);
  }
}

/**
 * Test dynamic package scanning for non-standard package signatures.
 */
function testDynamicPackageScan(): void {
  const sandbox = createSandbox();
  try {
    const localAppData = path.join(sandbox, 'AppData', 'Local');
    const packagesDir = path.join(localAppData, 'Packages');
    const customPkg = path.join(
      packagesDir,
      'Microsoft.MinecraftCustomBuild_xyz123',
      'LocalState',
      'games',
      'com.mojang'
    );
    const expectedPacks = path.join(customPkg, 'development_behavior_packs');
    fs.mkdirSync(expectedPacks, { recursive: true });

    const foundPkg = findMinecraftPackageDir(packagesDir);
    assert.ok(foundPkg);
    assert.ok(foundPkg.includes('Microsoft.MinecraftCustomBuild_xyz123'));

    const resolved = getDevelopmentPacksPath({ localAppData });
    assert.strictEqual(resolved, expectedPacks);
  } finally {
    cleanSandbox(sandbox);
  }
}

/**
 * Test standalone non-packaged launcher fallback resolution.
 */
function testStandaloneLauncherFallback(): void {
  const sandbox = createSandbox();
  try {
    const localAppData = path.join(sandbox, 'AppData', 'Local');
    const mojangDir = path.join(localAppData, 'Minecraft', 'LocalState', 'games', 'com.mojang');
    const expectedPacks = path.join(mojangDir, 'development_behavior_packs');
    fs.mkdirSync(expectedPacks, { recursive: true });

    const resolved = getDevelopmentPacksPath({ localAppData });
    assert.strictEqual(resolved, expectedPacks);
  } finally {
    cleanSandbox(sandbox);
  }
}

/**
 * Test explicit environment variable overrides.
 */
function testEnvironmentVariableOverrides(): void {
  const sandbox = createSandbox();
  try {
    const directDevPacks = path.join(sandbox, 'custom_dev_packs');
    fs.mkdirSync(directDevPacks, { recursive: true });

    const resolvedDirect = getDevelopmentPacksPath({
      customEnv: { MINECRAFT_DEV_PACKS_PATH: directDevPacks },
    });
    assert.strictEqual(resolvedDirect, directDevPacks);

    const bedrockBase = path.join(sandbox, 'bedrock_root');
    const mojangDir = path.join(bedrockBase, 'games', 'com.mojang');
    const expectedBehavior = path.join(mojangDir, 'development_behavior_packs');
    fs.mkdirSync(mojangDir, { recursive: true });

    const resolvedBase = getDevelopmentPacksPath({
      customEnv: { MINECRAFT_BEDROCK_PATH: bedrockBase },
    });
    assert.strictEqual(resolvedBase, expectedBehavior);
  } finally {
    cleanSandbox(sandbox);
  }
}

/**
 * Test auto-creation of development packs folder without admin privileges.
 */
function testAutoCreationWithoutAdmin(): void {
  const sandbox = createSandbox();
  try {
    const localAppData = path.join(sandbox, 'AppData', 'Local');
    const mojangDir = path.join(
      localAppData,
      'Packages',
      'Microsoft.MinecraftWindows_8wekyb3d8bbwe',
      'LocalState',
      'games',
      'com.mojang'
    );
    fs.mkdirSync(mojangDir, { recursive: true });

    const targetBehavior = path.join(mojangDir, 'development_behavior_packs');
    assert.strictEqual(fs.existsSync(targetBehavior), false);

    const resolved = getDevelopmentPacksPath({ localAppData, autoCreate: true });
    assert.strictEqual(resolved, targetBehavior);
    assert.strictEqual(fs.existsSync(targetBehavior), true);
  } finally {
    cleanSandbox(sandbox);
  }
}

/**
 * Test resource and skin pack resolution options.
 */
function testPackTypeOptions(): void {
  const sandbox = createSandbox();
  try {
    const localAppData = path.join(sandbox, 'AppData', 'Local');
    const mojangDir = path.join(
      localAppData,
      'Packages',
      'Microsoft.MinecraftWindows_8wekyb3d8bbwe',
      'LocalState',
      'games',
      'com.mojang'
    );
    fs.mkdirSync(mojangDir, { recursive: true });

    const resPath = getDevelopmentPacksPath({ localAppData, packType: 'resource' });
    assert.strictEqual(resPath, path.join(mojangDir, 'development_resource_packs'));
    assert.strictEqual(fs.existsSync(resPath), true);

    const skinPath = getDevelopmentPacksPath({ localAppData, packType: 'skin' });
    assert.strictEqual(skinPath, path.join(mojangDir, 'development_skin_packs'));
    assert.strictEqual(fs.existsSync(skinPath), true);
  } finally {
    cleanSandbox(sandbox);
  }
}

/**
 * Test ENOENT error handling when no installation exists.
 */
function testEnoentErrorHandling(): void {
  const sandbox = createSandbox();
  try {
    const emptyLocal = path.join(sandbox, 'empty_local');
    fs.mkdirSync(emptyLocal, { recursive: true });

    assert.throws(
      () => {
        getDevelopmentPacksPath({ localAppData: emptyLocal });
      },
      (err: Error) => {
        return err.message.includes('ENOENT: no such file or directory');
      }
    );
  } finally {
    cleanSandbox(sandbox);
  }
}

/**
 * Test resolveDevPacks alias function.
 */
function testResolveDevPacksAlias(): void {
  const sandbox = createSandbox();
  try {
    const localAppData = path.join(sandbox, 'AppData', 'Local');
    const mojangDir = path.join(
      localAppData,
      'Packages',
      'Microsoft.MinecraftWindows_8wekyb3d8bbwe',
      'LocalState',
      'games',
      'com.mojang'
    );
    fs.mkdirSync(mojangDir, { recursive: true });

    const resolved = resolveDevPacks({ localAppData });
    assert.strictEqual(resolved, path.join(mojangDir, 'development_behavior_packs'));
  } finally {
    cleanSandbox(sandbox);
  }
}

/**
 * Main test runner executing all isolated test cases.
 */
function runAllTests(): void {
  testLegacyUwpResolution();
  testModernWindowsResolution();
  testMapiResolution();
  testBetaResolution();
  testDynamicPackageScan();
  testStandaloneLauncherFallback();
  testEnvironmentVariableOverrides();
  testAutoCreationWithoutAdmin();
  testPackTypeOptions();
  testEnoentErrorHandling();
  testResolveDevPacksAlias();
  console.log('All 11 TypeScript isolated tests passed successfully.');
}

runAllTests();
