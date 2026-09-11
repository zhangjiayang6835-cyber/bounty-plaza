import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';
import {
  resolveBedrockDevPath,
  resolveMojangDevelopmentPath,
  getWindowsCandidatePaths,
  deploy,
  syncDirectory
} from '../scripts/deploy.js';

test('resolveBedrockDevPath returns custom destination when provided', () => {
  const custom = path.resolve('my/custom/bedrock/path');
  const result = resolveBedrockDevPath({ customDestination: custom });
  assert.equal(result, custom);

  const compatResult = resolveMojangDevelopmentPath(custom, 'behavior');
  assert.equal(compatResult, custom);
});

test('resolveBedrockDevPath respects MINECRAFT_DEVELOPMENT_PATH environment override', () => {
  const customEnvRoot = '/var/bedrock/server';
  const result = resolveBedrockDevPath({
    env: { MINECRAFT_DEVELOPMENT_PATH: customEnvRoot },
    packType: 'behavior'
  });
  assert.equal(result, path.resolve(customEnvRoot, 'development_behavior_packs'));

  const resourceResult = resolveBedrockDevPath({
    env: { MINECRAFT_DEVELOPMENT_PATH: customEnvRoot },
    packType: 'resource'
  });
  assert.equal(resourceResult, path.resolve(customEnvRoot, 'development_resource_packs'));
});

test('resolveBedrockDevPath respects BEDROCK_DEVELOPMENT_PATH environment override', () => {
  const customEnvRoot = '/opt/bedrock/workspace';
  const result = resolveBedrockDevPath({
    env: { BEDROCK_DEVELOPMENT_PATH: customEnvRoot },
    packType: 'behavior'
  });
  assert.equal(result, path.resolve(customEnvRoot, 'development_behavior_packs'));
});

test('resolveBedrockDevPath finds existing Windows UWP package directory', (t) => {
  const tmpBase = fs.mkdtempSync(path.join(os.tmpdir(), 'uwp_test_'));
  t.after(() => fs.rmSync(tmpBase, { recursive: true, force: true }));

  const localAppData = path.join(tmpBase, 'Local');
  const uwpPath = path.join(
    localAppData,
    'Packages',
    'Microsoft.MinecraftUWP_8wekyb3d8bbwe',
    'LocalState',
    'games',
    'com.mojang',
    'development_behavior_packs'
  );
  fs.mkdirSync(uwpPath, { recursive: true });

  const result = resolveBedrockDevPath({
    platform: 'win32',
    env: {
      LOCALAPPDATA: localAppData,
      APPDATA: path.join(tmpBase, 'Roaming')
    },
    homedir: tmpBase,
    packType: 'behavior'
  });

  assert.equal(result, uwpPath);
});

test('resolveBedrockDevPath finds existing Windows Roaming directory when UWP is absent', (t) => {
  const tmpBase = fs.mkdtempSync(path.join(os.tmpdir(), 'roaming_test_'));
  t.after(() => fs.rmSync(tmpBase, { recursive: true, force: true }));

  const appData = path.join(tmpBase, 'Roaming');
  const roamingPath = path.join(appData, '.minecraft', 'bedrock', 'development_behavior_packs');
  fs.mkdirSync(roamingPath, { recursive: true });

  const result = resolveBedrockDevPath({
    platform: 'win32',
    env: {
      LOCALAPPDATA: path.join(tmpBase, 'Local'),
      APPDATA: appData
    },
    homedir: tmpBase,
    packType: 'behavior'
  });

  assert.equal(result, roamingPath);
});

test('resolveBedrockDevPath finds existing macOS Application Support directory', (t) => {
  const tmpBase = fs.mkdtempSync(path.join(os.tmpdir(), 'darwin_test_'));
  t.after(() => fs.rmSync(tmpBase, { recursive: true, force: true }));

  const macPath = path.join(
    tmpBase,
    'Library',
    'Application Support',
    'mcpelauncher',
    'games',
    'com.mojang',
    'development_behavior_packs'
  );
  fs.mkdirSync(macPath, { recursive: true });

  const result = resolveBedrockDevPath({
    platform: 'darwin',
    homedir: tmpBase,
    packType: 'behavior'
  });

  assert.equal(result, macPath);
});

test('resolveBedrockDevPath finds existing Linux local share directory', (t) => {
  const tmpBase = fs.mkdtempSync(path.join(os.tmpdir(), 'linux_test_'));
  t.after(() => fs.rmSync(tmpBase, { recursive: true, force: true }));

  const linuxPath = path.join(
    tmpBase,
    '.local',
    'share',
    'mcpelauncher',
    'games',
    'com.mojang',
    'development_behavior_packs'
  );
  fs.mkdirSync(linuxPath, { recursive: true });

  const result = resolveBedrockDevPath({
    platform: 'linux',
    homedir: tmpBase,
    packType: 'behavior'
  });

  assert.equal(result, linuxPath);
});

test('getWindowsCandidatePaths returns prioritized list of Win32 paths', () => {
  const fakeEnv = {
    APPDATA: 'C:\\Users\\Test\\AppData\\Roaming',
    LOCALAPPDATA: 'C:\\Users\\Test\\AppData\\Local'
  };
  const candidates = getWindowsCandidatePaths(fakeEnv, 'C:\\Users\\Test', 'development_behavior_packs');
  assert.ok(candidates.length >= 4);
  assert.ok(candidates[0].includes('.minecraft'));
  assert.ok(candidates.some(c => c.includes('Microsoft.MinecraftUWP_8wekyb3d8bbwe')));
});

test('deploy auto-creates missing destination directory without ENOENT failure', (t) => {
  const tmpBase = fs.mkdtempSync(path.join(os.tmpdir(), 'deploy_test_'));
  t.after(() => fs.rmSync(tmpBase, { recursive: true, force: true }));

  const missingDest = path.join(tmpBase, 'non_existent_folder', 'development_behavior_packs');
  assert.equal(fs.existsSync(missingDest), false);

  const sourceDir = path.join(tmpBase, 'source_pack');
  fs.mkdirSync(sourceDir, { recursive: true });
  fs.writeFileSync(path.join(sourceDir, 'manifest.json'), '{"format_version": 2}');

  const result = deploy({
    customDestination: missingDest,
    sourceDir,
    autoCreate: true
  });

  assert.equal(result.success, true);
  assert.equal(result.destination, missingDest);
  assert.equal(fs.existsSync(missingDest), true);
  assert.equal(fs.existsSync(path.join(missingDest, 'manifest.json')), true);
  assert.equal(result.copiedCount, 1);
});

test('deploy falls back to local dist when autoCreate is false', (t) => {
  const tmpBase = fs.mkdtempSync(path.join(os.tmpdir(), 'fallback_test_'));
  t.after(() => fs.rmSync(tmpBase, { recursive: true, force: true }));

  const missingDest = path.join(tmpBase, 'missing_dev_dir');
  const localDistRoot = path.join(tmpBase, 'custom_dist');
  const sourceDir = path.join(tmpBase, 'source_pack');
  fs.mkdirSync(sourceDir, { recursive: true });
  fs.writeFileSync(path.join(sourceDir, 'pack.json'), '{"id":"test"}');

  const result = deploy({
    customDestination: missingDest,
    sourceDir,
    autoCreate: false,
    localDistRoot
  });

  assert.equal(result.success, true);
  assert.equal(result.fallbackUsed, true);
  assert.ok(result.destination.startsWith(localDistRoot));
  assert.equal(fs.existsSync(result.destination), true);
});

test('syncDirectory performs differential copy and clean removal', (t) => {
  const tmpBase = fs.mkdtempSync(path.join(os.tmpdir(), 'sync_test_'));
  t.after(() => fs.rmSync(tmpBase, { recursive: true, force: true }));

  const src = path.join(tmpBase, 'src');
  const dst = path.join(tmpBase, 'dst');
  fs.mkdirSync(src, { recursive: true });
  fs.mkdirSync(dst, { recursive: true });

  fs.writeFileSync(path.join(src, 'file1.txt'), 'hello');
  fs.writeFileSync(path.join(src, 'file2.txt'), 'world');
  fs.writeFileSync(path.join(dst, 'obsolete.txt'), 'stale');

  const stats1 = syncDirectory(src, dst, { clean: true });
  assert.equal(stats1.copied, 2);
  assert.equal(stats1.removed, 1);
  assert.equal(fs.existsSync(path.join(dst, 'obsolete.txt')), false);
  assert.equal(fs.readFileSync(path.join(dst, 'file1.txt'), 'utf-8'), 'hello');

  const stats2 = syncDirectory(src, dst, { clean: true });
  assert.equal(stats2.copied, 0);
  assert.equal(stats2.removed, 0);
});
