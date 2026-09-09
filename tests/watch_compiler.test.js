/**
 * Automated test suite for scripts/watch.js intermediate build filter pipeline.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';

import {
  stripComments,
  deepMerge,
  compileJsonte,
  compileSoundDefinitions,
  deployDirect,
} from '../scripts/watch.js';

test('stripComments removes single and multi-line comments from JSON content', () => {
  const input = `{
    // Single line comment
    "format_version": "1.20.0", /* Multi line comment */
    "minecraft:item": {
      "description": {
        "identifier": "custom:ruby_sword", // Trailing comment
      },
    },
  }`;

  const cleaned = stripComments(input);
  const parsed = JSON.parse(cleaned);
  assert.equal(parsed.format_version, '1.20.0');
  assert.equal(parsed['minecraft:item'].description.identifier, 'custom:ruby_sword');
});

test('deepMerge merges objects recursively while child overrides primitives', () => {
  const base = {
    a: 1,
    nested: {
      foo: 'base_foo',
      bar: 'base_bar',
    },
    list: [1, 2],
  };

  const override = {
    nested: {
      bar: 'child_bar',
      baz: 'child_baz',
    },
    list: [3, 4],
  };

  const result = deepMerge(base, override);
  assert.equal(result.a, 1);
  assert.equal(result.nested.foo, 'base_foo');
  assert.equal(result.nested.bar, 'child_bar');
  assert.equal(result.nested.baz, 'child_baz');
  assert.deepEqual(result.list, [3, 4]);
});

test('compileJsonte expands variables and strips meta directives', () => {
  const template = `{
    "$scope": {
      "item_name": "ruby_dagger",
      "attack_damage": 7
    },
    "format_version": "1.20.0",
    "minecraft:item": {
      "description": {
        "identifier": "custom:{{item_name}}"
      },
      "components": {
        "minecraft:damage": "{{attack_damage}}"
      }
    }
  }`;

  const output = compileJsonte(template);
  const parsed = JSON.parse(output);

  assert.equal(parsed.format_version, '1.20.0');
  assert.equal(parsed['minecraft:item'].description.identifier, 'custom:ruby_dagger');
  assert.equal(parsed['minecraft:item'].components['minecraft:damage'], 7);
  assert.equal(parsed.$scope, undefined);
});

test('compileJsonte expands {{#each}} array loops', () => {
  const template = `{
    "format_version": "1.20.0",
    "minecraft:recipe_shaped": {
      "result": [
        {
          "{{#each ['ruby', 'sapphire']}}": {
            "item": "custom:{{$value}}_ingot",
            "count": 1
          }
        }
      ]
    }
  }`;

  const output = compileJsonte(template);
  const parsed = JSON.parse(output);
  const results = parsed['minecraft:recipe_shaped'].result;

  assert.equal(results.length, 2);
  assert.equal(results[0].item, 'custom:ruby_ingot');
  assert.equal(results[1].item, 'custom:sapphire_ingot');
});

test('compileJsonte resolves $extend from external parent template', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'jsonte_test_'));
  const parentPath = path.join(tmpDir, 'base_tool.jsonte');
  fs.writeFileSync(parentPath, JSON.stringify({
    format_version: '1.20.0',
    'minecraft:item': {
      description: {
        category: 'Equipment',
      },
      components: {
        'minecraft:max_stack_size': 1,
        'minecraft:hand_equipped': true,
      },
    },
  }));

  const childContent = `{
    "$extend": "${parentPath.replace(/\\/g, '/')}",
    "minecraft:item": {
      "description": {
        "identifier": "custom:ruby_pickaxe"
      },
      "components": {
        "minecraft:durability": {
          "max_durability": 1561
        }
      }
    }
  }`;

  const output = compileJsonte(childContent, {}, tmpDir);
  const parsed = JSON.parse(output);

  assert.equal(parsed.format_version, '1.20.0');
  assert.equal(parsed['minecraft:item'].description.category, 'Equipment');
  assert.equal(parsed['minecraft:item'].description.identifier, 'custom:ruby_pickaxe');
  assert.equal(parsed['minecraft:item'].components['minecraft:max_stack_size'], 1);
  assert.equal(parsed['minecraft:item'].components['minecraft:durability'].max_durability, 1561);
  assert.equal(parsed.$extend, undefined);

  fs.rmSync(tmpDir, { recursive: true, force: true });
});

test('deployDirect executes filters, compiles templates, and preserves source files', () => {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'deploy_test_'));
  const srcDir = path.join(tmpRoot, 'source', 'resources', 'data');
  const destDir = path.join(tmpRoot, 'com.mojang', 'development_behavior_packs', 'my_pack');

  fs.mkdirSync(srcDir, { recursive: true });

  const templateContent = `{
    // Source template
    "$scope": { "tool_tier": "ruby" },
    "format_version": "1.20.0",
    "minecraft:item": {
      "description": {
        "identifier": "custom:{{tool_tier}}_sword"
      }
    }
  }`;
  const srcFile = path.join(srcDir, 'ruby_sword.jsonte');
  fs.writeFileSync(srcFile, templateContent, 'utf8');

  const staticContent = '{"static": true}';
  const staticFile = path.join(srcDir, 'static.json');
  fs.writeFileSync(staticFile, staticContent, 'utf8');

  const srcHashBefore = crypto.createHash('sha256').update(fs.readFileSync(srcFile)).digest('hex');

  const deployStats = deployDirect(srcDir, destDir);

  assert.equal(deployStats.filesProcessed, 2);
  assert.equal(deployStats.templatesCompiled, 1);

  const srcHashAfter = crypto.createHash('sha256').update(fs.readFileSync(srcFile)).digest('hex');
  assert.equal(srcHashBefore, srcHashAfter, 'Source file must remain strictly unmodified');

  const destFile = path.join(destDir, 'ruby_sword.json');
  assert.ok(fs.existsSync(destFile), 'Destination should have .json output');
  assert.ok(!fs.existsSync(path.join(destDir, 'ruby_sword.jsonte')), 'No raw .jsonte in destination');

  const compiled = JSON.parse(fs.readFileSync(destFile, 'utf8'));
  assert.equal(compiled['minecraft:item'].description.identifier, 'custom:ruby_sword');
  assert.equal(compiled.$scope, undefined);
  assert.equal(compiled.$extend, undefined);

  const secondRun = deployDirect(srcDir, destDir);
  assert.equal(secondRun.cached, 2, 'Second run should leverage incremental cache');

  fs.rmSync(tmpRoot, { recursive: true, force: true });
});

test('compileSoundDefinitions scans audio directory and produces valid Bedrock format', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'sound_test_'));
  const soundDir = path.join(tmpDir, 'sounds', 'custom');
  fs.mkdirSync(soundDir, { recursive: true });

  fs.writeFileSync(path.join(soundDir, 'ruby_swing1.ogg'), 'mock_audio');
  fs.writeFileSync(path.join(soundDir, 'ruby_swing2.ogg'), 'mock_audio');

  const defs = compileSoundDefinitions(path.join(tmpDir, 'sounds'));
  assert.equal(defs.format_version, '1.20.0');
  assert.ok(defs.sound_definitions['custom.ruby_swing']);
  assert.equal(defs.sound_definitions['custom.ruby_swing'].category, 'player');
  assert.equal(defs.sound_definitions['custom.ruby_swing'].sounds.length, 2);
  assert.ok(defs.sound_definitions['custom.ruby_swing'].sounds.includes('sounds/custom/ruby_swing1'));

  fs.rmSync(tmpDir, { recursive: true, force: true });
});
