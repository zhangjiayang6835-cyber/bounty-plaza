import { test, describe, afterEach } from 'node:test';
import assert from 'node:assert';
import * as fs from 'fs';
import * as path from 'path';
import { generateBlockFamilies, BlockFamilyBuilder } from '../tools/family_builder.js';
import { runBuild, BuildPipeline } from '../tools/build.js';

describe('Block Family Catalog Generator & Cache Independence Invariants (#9)', () => {
  const stagingTestDir = path.resolve('_test_family_temp');
  const distTestDir = path.resolve('_test_family_dist');

  afterEach(() => {
    if (fs.existsSync(stagingTestDir)) {
      fs.rmSync(stagingTestDir, { recursive: true, force: true });
    }
    if (fs.existsSync(distTestDir)) {
      fs.rmSync(distTestDir, { recursive: true, force: true });
    }
  });

  test('reproduces failure when requireExisting is asserted against wiped cache', () => {
    const catalogPath = path.join(stagingTestDir, 'block_families.json');
    if (fs.existsSync(stagingTestDir)) {
      fs.rmSync(stagingTestDir, { recursive: true, force: true });
    }

    assert.throws(
      () => {
        generateBlockFamilies({
          stagingBase: stagingTestDir,
          catalogPath,
          requireExisting: true,
        });
      },
      (err) => {
        assert.ok(err instanceof Error);
        assert.strictEqual(
          err.message,
          `Missing block family catalog: '${catalogPath}' not found.`
        );
        return true;
      }
    );
  });

  test('generates fresh catalog deterministically on a clean run without pre-existing cache', () => {
    const catalogPath = path.join(stagingTestDir, 'block_families.json');
    assert.strictEqual(fs.existsSync(catalogPath), false);

    const catalog = generateBlockFamilies({
      stagingBase: stagingTestDir,
      catalogPath,
      sourceDir: 'packs/behavior_pack',
    });

    assert.ok(catalog);
    assert.strictEqual(fs.existsSync(catalogPath), true);
    assert.strictEqual(catalog.format_version, '1.20.80');
    assert.ok(catalog.statistics.total_families >= 2);
    assert.ok(catalog.statistics.total_blocks >= 4);

    const content = fs.readFileSync(catalogPath, 'utf-8');
    const parsed = JSON.parse(content);
    assert.deepStrictEqual(parsed.families, catalog.families);
    assert.strictEqual(parsed.checksum, catalog.checksum);
  });

  test('overwrites stale corrupt cache without relying on stale metadata', () => {
    const catalogPath = path.join(stagingTestDir, 'block_families.json');
    fs.mkdirSync(stagingTestDir, { recursive: true });
    fs.writeFileSync(
      catalogPath,
      JSON.stringify({ stale: true, invalid_state: 'corrupt_cache' }),
      'utf-8'
    );
    assert.ok(fs.existsSync(catalogPath));

    const freshCatalog = generateBlockFamilies({
      stagingBase: stagingTestDir,
      catalogPath,
      sourceDir: 'packs/behavior_pack',
    });

    const parsed = JSON.parse(fs.readFileSync(catalogPath, 'utf-8'));
    assert.strictEqual(parsed.stale, undefined);
    assert.strictEqual(parsed.invalid_state, undefined);
    assert.ok(parsed.families.custom);
    assert.strictEqual(parsed.families.custom.name, 'custom');
  });

  test('executes runBuild cleanly end-to-end after cache wiping', () => {
    const pipeline = new BuildPipeline({
      sourceDir: 'packs/behavior_pack',
      stagingDir: path.join(stagingTestDir, 'behavior_pack'),
      destDir: distTestDir,
      clean: true,
    });

    pipeline.clean();
    assert.strictEqual(fs.existsSync(stagingTestDir), false);

    const result = runBuild({
      sourceDir: 'packs/behavior_pack',
      stagingDir: path.join(stagingTestDir, 'behavior_pack'),
      stagingBase: stagingTestDir,
      destDir: distTestDir,
      clean: true,
    });

    assert.strictEqual(result.success, true);
    assert.ok(result.stats.families);
    assert.ok(result.stats.families.statistics.total_families >= 2);

    const deployedCatalogPath = path.join(distTestDir, 'block_families.json');
    assert.ok(fs.existsSync(deployedCatalogPath));

    const deployedCatalog = JSON.parse(fs.readFileSync(deployedCatalogPath, 'utf-8'));
    assert.strictEqual(deployedCatalog.format_version, '1.20.80');
    assert.strictEqual(deployedCatalog.checksum, result.stats.families.checksum);
  });

  test('validates block family shape mapping and member grouping', () => {
    const builder = new BlockFamilyBuilder({
      stagingBase: stagingTestDir,
      sourceDir: 'packs/behavior_pack',
    });

    const catalog = builder.compileCatalog();
    assert.ok(catalog.families.custom);
    assert.strictEqual(catalog.families.custom.base, 'tank:custom_block');
    assert.strictEqual(catalog.families.custom.members.slab, 'tank:custom_slab');
    assert.strictEqual(catalog.families.custom.members.stair, 'tank:custom_stair');
    assert.strictEqual(catalog.families.custom.members.base, 'tank:custom_block');

    assert.strictEqual(catalog.block_to_family['tank:custom_block'], 'custom');
    assert.strictEqual(catalog.block_to_family['tank:custom_slab'], 'custom');
    assert.strictEqual(catalog.block_to_family['tank:custom_stair'], 'custom');

    assert.strictEqual(catalog.statistics.shape_counts.slab >= 1, true);
    assert.strictEqual(catalog.statistics.shape_counts.stair >= 1, true);
    assert.strictEqual(catalog.statistics.shape_counts.base >= 2, true);
  });

  test('produces identical deterministic checksum across repeat executions', () => {
    const builder1 = new BlockFamilyBuilder({
      stagingBase: stagingTestDir,
      sourceDir: 'packs/behavior_pack',
    });
    const catalog1 = builder1.compileCatalog();

    const builder2 = new BlockFamilyBuilder({
      stagingBase: stagingTestDir,
      sourceDir: 'packs/behavior_pack',
    });
    const catalog2 = builder2.compileCatalog();

    assert.strictEqual(catalog1.checksum, catalog2.checksum);
    assert.deepStrictEqual(catalog1.families, catalog2.families);
  });

  test('gracefully handles empty source directory without crashing', () => {
    const emptyDir = path.join(stagingTestDir, 'empty_pack');
    fs.mkdirSync(emptyDir, { recursive: true });

    const builder = new BlockFamilyBuilder({
      stagingBase: stagingTestDir,
      sourceDir: emptyDir,
    });

    const catalog = builder.compileCatalog();
    assert.strictEqual(catalog.format_version, '1.20.80');
    assert.strictEqual(catalog.statistics.total_families, 0);
    assert.strictEqual(catalog.statistics.total_blocks, 0);
    assert.deepStrictEqual(catalog.families, {});
  });
});
