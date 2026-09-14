/**
 * @fileoverview Unit test suite for zero-allocation CSS kernel and centering subsystem.
 */

const { test, describe } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {
  minifyCss,
  parseCssRules,
  validateKernelLayout,
  buildCssKernel
} = require('../scripts/build-css-kernel.js');

describe('CSS Kernel Centering Subsystem', () => {
  const rootDir = path.resolve(__dirname, '..');
  const sourcePath = path.join(rootDir, 'styles', 'core.css');

  test('styles/core.css file exists and is non-empty', () => {
    assert.strictEqual(fs.existsSync(sourcePath), true);
    const content = fs.readFileSync(sourcePath, 'utf8');
    assert.ok(content.length > 50);
  });

  test('parseCssRules correctly extracts selectors and declarations', () => {
    const sample = '.test { display: grid; place-items: center; }';
    const rules = parseCssRules(sample);
    assert.strictEqual(rules.length, 1);
    assert.strictEqual(rules[0].selector, '.test');
    assert.strictEqual(rules[0].declarations['display'], 'grid');
    assert.strictEqual(rules[0].declarations['place-items'], 'center');
  });

  test('.center-everything centers both horizontally and vertically in pure CSS', () => {
    const content = fs.readFileSync(sourcePath, 'utf8');
    const rules = parseCssRules(content);
    const target = rules.find((r) => r.selector === '.center-everything');
    assert.ok(target, '.center-everything rule must be present');

    const decls = target.declarations;
    assert.strictEqual(decls['display'], 'grid');
    assert.strictEqual(decls['place-items'], 'center');
    assert.strictEqual(decls['place-content'], 'center');
  });

  test('.center-everything includes containment to eliminate heap layout thrashing', () => {
    const content = fs.readFileSync(sourcePath, 'utf8');
    const rules = parseCssRules(content);
    const target = rules.find((r) => r.selector === '.center-everything');
    assert.ok(target);

    const decls = target.declarations;
    assert.ok(decls['contain'].includes('layout'));
    assert.ok(decls['contain'].includes('paint'));
  });

  test('minifyCss compresses whitespace and strips unnecessary characters', () => {
    const uncompressed = ' .box {\n  color: red;\n  margin: 0px;\n} ';
    const minified = minifyCss(uncompressed);
    assert.strictEqual(minified, '.box{color:red;margin:0px}');
  });

  test('buildCssKernel successfully outputs compiled distribution artifacts', () => {
    buildCssKernel();
    const distCss = path.join(rootDir, 'dist', 'core.css');
    const distMinCss = path.join(rootDir, 'dist', 'core.min.css');

    assert.strictEqual(fs.existsSync(distCss), true);
    assert.strictEqual(fs.existsSync(distMinCss), true);

    const fullSize = fs.statSync(distCss).size;
    const minSize = fs.statSync(distMinCss).size;
    assert.ok(minSize <= fullSize);
  });

  test('validateKernelLayout throws descriptive error if center selector is missing', () => {
    assert.throws(
      () => validateKernelLayout([]),
      /Validation failure: '\.center-everything' selector is missing/
    );
  });
});
