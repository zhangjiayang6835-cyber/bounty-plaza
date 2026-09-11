import { test, describe, before, after } from 'node:test';
import assert from 'node:assert';
import * as fs from 'fs';
import * as path from 'path';
import { BuildPipeline } from '../tools/build.js';
import { PackValidator } from '../tools/pack_validator.js';
import { TemplateExpander } from '../tools/template_expander.js';
import { syncDirectory, resolveMojangDevelopmentPath } from '../tools/sync.js';

describe('Bedrock Build Pipeline & Template Expansion Invariants', () => {
  const testOutputDir = path.resolve('_test_dist');
  const testStagingDir = path.resolve('_test_temp');

  after(() => {
    if (fs.existsSync(testOutputDir)) {
      fs.rmSync(testOutputDir, { recursive: true, force: true });
    }
    if (fs.existsSync(testStagingDir)) {
      fs.rmSync(testStagingDir, { recursive: true, force: true });
    }
  });

  test('reproduces BDS syntax error when parsing unexpanded raw template directly', () => {
    const report = PackValidator.validatePack('packs/behavior_pack');
    assert.strictEqual(report.valid, false);

    const stairError = report.errors.find((err) =>
      err.includes("Failed to parse JSON in 'blocks/custom_stair.json'")
    );
    assert.ok(stairError, 'Expected error for custom_stair.json');
    assert.ok(
      stairError.includes("Syntax error: unexpected character '{' at line 4 column 12"),
      `Error should identify line 4 column 12 unexpected character '{'. Got:\n${stairError}`
    );
  });

  test('executes pipeline in order: expand to _temp/ then validate then synchronize', () => {
    const pipeline = new BuildPipeline({
      sourceDir: 'packs/behavior_pack',
      stagingDir: testStagingDir,
      destDir: testOutputDir,
      clean: true,
    });

    const result = pipeline.run();
    assert.strictEqual(result.success, true);
    assert.strictEqual(result.stats.staging.expandedCount >= 2, true);
    assert.strictEqual(result.stats.validation.fileCount >= 4, true);
    assert.strictEqual(result.stats.sync.copied >= 4, true);

    const deployedReport = PackValidator.validatePack(testOutputDir);
    assert.strictEqual(deployedReport.valid, true);
    assert.strictEqual(deployedReport.errors.length, 0);
  });

  test('validates expanded custom_stair.json schema, states, and permutations', () => {
    const stairPath = path.join(testOutputDir, 'blocks', 'custom_stair.json');
    assert.ok(fs.existsSync(stairPath), 'custom_stair.json must exist in deployed pack');

    const content = fs.readFileSync(stairPath, 'utf-8');
    assert.strictEqual(content.includes('{{'), false);
    assert.strictEqual(content.includes('}}'), false);

    const json = JSON.parse(content);
    assert.strictEqual(json.format_version, '1.20.80');
    assert.strictEqual(json['minecraft:block'].description.identifier, 'tank:custom_stair');

    const states = json['minecraft:block'].description.states;
    assert.deepStrictEqual(states['tank:facing'], [0, 1, 2, 3]);
    assert.deepStrictEqual(states['tank:upside_down'], [false, true]);

    const perms = json['minecraft:block'].permutations;
    assert.strictEqual(Array.isArray(perms), true);
    assert.strictEqual(perms.length, 5);
  });

  test('validates custom_slab.json JSONTE scope substitution and metadata pruning', () => {
    const slabPath = path.join(testOutputDir, 'blocks', 'custom_slab.json');
    assert.ok(fs.existsSync(slabPath));

    const content = fs.readFileSync(slabPath, 'utf-8');
    assert.strictEqual(content.includes('$scope'), false);
    assert.strictEqual(content.includes('{{'), false);

    const json = JSON.parse(content);
    assert.strictEqual(json['minecraft:block'].description.identifier, 'tank:custom_slab');
    assert.strictEqual(
      json['minecraft:block'].components['minecraft:material_instances']['*'].texture,
      'custom_slab_texture'
    );
  });

  test('enforces clean-slate invariant by wiping stale cached templates', () => {
    const staleFilePath = path.join(testStagingDir, 'blocks', 'stale_zombie_block.json');
    fs.mkdirSync(path.dirname(staleFilePath), { recursive: true });
    fs.writeFileSync(staleFilePath, '{"format_version":"1.20.80"}', 'utf-8');
    assert.ok(fs.existsSync(staleFilePath));

    const pipeline = new BuildPipeline({
      sourceDir: 'packs/behavior_pack',
      stagingDir: testStagingDir,
      destDir: testOutputDir,
      clean: true,
    });

    pipeline.run();
    assert.strictEqual(fs.existsSync(staleFilePath), false);
    assert.strictEqual(fs.existsSync(path.join(testOutputDir, 'blocks', 'stale_zombie_block.json')), false);
  });

  test('preserves non-templated static assets with exact byte equality', () => {
    const sourceManifest = fs.readFileSync('packs/behavior_pack/manifest.json');
    const deployedManifest = fs.readFileSync(path.join(testOutputDir, 'manifest.json'));
    assert.strictEqual(sourceManifest.equals(deployedManifest), true);

    const sourceItem = fs.readFileSync('packs/behavior_pack/items/mannequin_wrench.json');
    const deployedItem = fs.readFileSync(path.join(testOutputDir, 'items', 'mannequin_wrench.json'));
    assert.strictEqual(sourceItem.equals(deployedItem), true);
  });

  test('synchronizes deletions cleanly from staging to destination', () => {
    const orphanFile = path.join(testOutputDir, 'blocks', 'orphan_old_stair.json');
    fs.writeFileSync(orphanFile, '{"test":true}', 'utf-8');
    assert.ok(fs.existsSync(orphanFile));

    const pipeline = new BuildPipeline({
      sourceDir: 'packs/behavior_pack',
      stagingDir: testStagingDir,
      destDir: testOutputDir,
      clean: true,
    });

    const result = pipeline.run();
    assert.strictEqual(fs.existsSync(orphanFile), false);
    assert.strictEqual(result.stats.sync.removed >= 1, true);
  });

  test('resolves com.mojang development destination path and respects custom paths', () => {
    const custom = resolveMojangDevelopmentPath('/custom/mojang/path', 'behavior');
    assert.strictEqual(custom, path.resolve('/custom/mojang/path'));

    const fallback = resolveMojangDevelopmentPath('', 'behavior');
    assert.ok(fallback.endsWith(path.join('dist', 'behavior_pack')));
  });
});
