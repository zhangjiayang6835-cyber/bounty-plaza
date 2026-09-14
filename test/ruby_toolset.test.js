import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {
  decodePng,
  encodePng,
  rgbToHsv,
  hsvToRgb,
  isDiamondColor,
  shiftPixelToRuby,
  generateRubyTexture,
  generateRubyToolset,
  parseCommandLineArgs,
  TOOLSET_ITEMS,
  CANONICAL_DIAMOND_BASE64
} from '../scripts/tools/generate_ruby_toolset.js';

test('rgbToHsv and hsvToRgb round-trip identity', () => {
  const testColors = [
    { r: 255, g: 0, b: 0 },
    { r: 0, g: 255, b: 0 },
    { r: 0, g: 0, b: 255 },
    { r: 164, g: 253, b: 240 },
    { r: 51, g: 235, b: 203 },
    { r: 43, g: 199, b: 172 },
    { r: 14, g: 63, b: 54 },
    { r: 8, g: 37, b: 32 },
    { r: 73, g: 54, b: 21 },
    { r: 104, g: 78, b: 30 }
  ];

  for (const color of testColors) {
    const { h, s, v } = rgbToHsv(color.r, color.g, color.b);
    const converted = hsvToRgb(h, s, v);
    assert.strictEqual(converted.r, color.r);
    assert.strictEqual(converted.g, color.g);
    assert.strictEqual(converted.b, color.b);
  }
});

test('isDiamondColor accurately discriminates diamond and handle pixels', () => {
  const diamondGlint = rgbToHsv(164, 253, 240);
  assert.strictEqual(isDiamondColor(diamondGlint.h, diamondGlint.s, diamondGlint.v), true);

  const diamondMidtone = rgbToHsv(43, 199, 172);
  assert.strictEqual(isDiamondColor(diamondMidtone.h, diamondMidtone.s, diamondMidtone.v), true);

  const diamondOutline = rgbToHsv(8, 37, 32);
  assert.strictEqual(isDiamondColor(diamondOutline.h, diamondOutline.s, diamondOutline.v), true);

  const stickColor = rgbToHsv(104, 78, 30);
  assert.strictEqual(isDiamondColor(stickColor.h, stickColor.s, stickColor.v), false);

  const stickDark = rgbToHsv(40, 30, 11);
  assert.strictEqual(isDiamondColor(stickDark.h, stickDark.s, stickDark.v), false);
});

test('shiftPixelToRuby enforces zero-bleed transparent masking', () => {
  const transparentPixel = { r: 164, g: 253, b: 240, a: 0 };
  const transformed = shiftPixelToRuby(transparentPixel);

  assert.strictEqual(transformed.a, 0);
  assert.strictEqual(transformed.r, 0);
  assert.strictEqual(transformed.g, 0);
  assert.strictEqual(transformed.b, 0);
});

test('shiftPixelToRuby preserves stick and non-diamond pixels unchanged', () => {
  const stickPixel = { r: 104, g: 78, b: 30, a: 255 };
  const transformed = shiftPixelToRuby(stickPixel);

  assert.strictEqual(transformed.r, 104);
  assert.strictEqual(transformed.g, 78);
  assert.strictEqual(transformed.b, 30);
  assert.strictEqual(transformed.a, 255);
});

test('shiftPixelToRuby maps diamond blues to authentic ruby reds while preserving V', () => {
  const diamondPixel = { r: 43, g: 199, b: 172, a: 255 };
  const originalHsv = rgbToHsv(diamondPixel.r, diamondPixel.g, diamondPixel.b);
  const transformed = shiftPixelToRuby(diamondPixel);
  const transformedHsv = rgbToHsv(transformed.r, transformed.g, transformed.b);

  assert.strictEqual(transformed.a, 255);
  assert.ok(
    transformedHsv.h >= 340 || transformedHsv.h <= 10,
    `Expected ruby hue (>=340 or <=10), got ${transformedHsv.h}`
  );
  assert.ok(
    Math.abs(transformedHsv.v - originalHsv.v) <= 0.05,
    `Expected preserved V gradation, original=${originalHsv.v}, transformed=${transformedHsv.v}`
  );
});

test('generateRubyToolset generates all five 16x16 PNG assets with valid dimensions and alpha', async () => {
  const tempOutputDir = path.resolve('textures/test_output');
  if (fs.existsSync(tempOutputDir)) {
    fs.rmSync(tempOutputDir, { recursive: true, force: true });
  }

  const results = await generateRubyToolset({
    inputDir: 'textures/items',
    outputDir: tempOutputDir
  });

  assert.strictEqual(results.length, 5);

  for (const item of TOOLSET_ITEMS) {
    const expectedFilePath = path.join(tempOutputDir, `ruby_${item}.png`);
    assert.ok(fs.existsSync(expectedFilePath));

    const fileBuffer = fs.readFileSync(expectedFilePath);
    const decoded = decodePng(fileBuffer);

    assert.strictEqual(decoded.width, 16);
    assert.strictEqual(decoded.height, 16);

    let transparentCount = 0;
    let opaqueCount = 0;

    for (let y = 0; y < 16; y++) {
      for (let x = 0; x < 16; x++) {
        const pixel = decoded.pixels[y][x];
        if (pixel.a === 0) {
          transparentCount++;
          assert.strictEqual(pixel.r, 0);
          assert.strictEqual(pixel.g, 0);
          assert.strictEqual(pixel.b, 0);
        } else {
          opaqueCount++;
          assert.strictEqual(pixel.a, 255);
        }
      }
    }

    assert.ok(transparentCount > 0);
    assert.ok(opaqueCount > 0);
    assert.strictEqual(transparentCount + opaqueCount, 256);
  }

  fs.rmSync(tempOutputDir, { recursive: true, force: true });
});

test('generateRubyTexture operates deterministically with identical SHA-256 digests', () => {
  const sourceBuffer = Buffer.from(CANONICAL_DIAMOND_BASE64.sword, 'base64');
  const runA = generateRubyTexture(sourceBuffer);
  const runB = generateRubyTexture(sourceBuffer);

  const hashA = crypto.createHash('sha256').update(runA).digest('hex');
  const hashB = crypto.createHash('sha256').update(runB).digest('hex');

  assert.strictEqual(hashA, hashB);
  assert.ok(runA.length > 0);
});

test('parseCommandLineArgs correctly extracts CLI flags', () => {
  const flags = [
    '--input-dir', 'assets/custom_input',
    '--output-dir', 'assets/custom_output',
    '--items', 'sword,axe',
    '--target-hue', '348'
  ];

  const parsed = parseCommandLineArgs(flags);
  assert.strictEqual(parsed.inputDir, 'assets/custom_input');
  assert.strictEqual(parsed.outputDir, 'assets/custom_output');
  assert.deepStrictEqual(parsed.items, ['sword', 'axe']);
  assert.strictEqual(parsed.targetHue, 348);
});
