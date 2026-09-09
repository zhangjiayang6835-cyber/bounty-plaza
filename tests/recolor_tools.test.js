const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const {
  recolorToRuby,
  recolorPixel,
  recolorRawBuffer,
  generateRubyToolsets,
  encodePNG,
  decodePNG,
  colorDistance,
  isDiamondMaterial,
  interpolateRubyRamp,
  PALETTE_MAP,
  VANILLA_DIAMOND_TOOLS
} = require('../scripts/recolor-tools.js');

test('recolorPixel converts diamond specular highlight to warm peach-pink gleam', () => {
  const [r, g, b, a] = recolorPixel(188, 252, 252, 255);
  assert.equal(r, 255);
  assert.equal(g, 205);
  assert.equal(b, 218);
  assert.equal(a, 255);
});

test('recolorPixel converts secondary diamond highlight', () => {
  const [r, g, b, a] = recolorPixel(155, 244, 242, 255);
  assert.equal(r, 255);
  assert.equal(g, 185);
  assert.equal(b, 195);
  assert.equal(a, 255);
});

test('recolorPixel converts diamond midtone to saturated crimson', () => {
  const [r, g, b, a] = recolorPixel(45, 194, 191, 255);
  assert.equal(r, 196);
  assert.equal(g, 35);
  assert.equal(b, 60);
  assert.equal(a, 255);
});

test('recolorPixel converts diamond dark facet to rich wine burgundy', () => {
  const [r, g, b, a] = recolorPixel(32, 139, 139, 255);
  assert.equal(r, 140);
  assert.equal(g, 19);
  assert.equal(b, 40);
  assert.equal(a, 255);
});

test('recolorPixel converts diamond outline to deep maroon silhouette', () => {
  const [r, g, b, a] = recolorPixel(25, 95, 95, 255);
  assert.equal(r, 84);
  assert.equal(g, 9);
  assert.equal(b, 23);
  assert.equal(a, 255);
});

test('recolorPixel strictly preserves wood handle pixels without modification', () => {
  const woodTones = [
    [143, 103, 60, 255],
    [110, 77, 37, 255],
    [75, 49, 20, 255],
    [46, 29, 12, 255]
  ];

  for (const tone of woodTones) {
    const result = recolorPixel(tone[0], tone[1], tone[2], tone[3]);
    assert.deepEqual(result, tone);
  }
});

test('recolorPixel preserves full transparency without color bleeding', () => {
  const transparentPixels = [
    [0, 0, 0, 0],
    [10, 20, 30, 0],
    [188, 252, 252, 0]
  ];

  for (const pixel of transparentPixels) {
    const result = recolorPixel(pixel[0], pixel[1], pixel[2], pixel[3]);
    assert.equal(result[3], 0);
  }
});

test('recolorPixel preserves partial alpha transparency for anti-aliased pixels', () => {
  const [r, g, b, a] = recolorPixel(45, 194, 191, 160);
  assert.equal(r, 196);
  assert.equal(g, 35);
  assert.equal(b, 60);
  assert.equal(a, 160);
});

test('PNG round-trip encoding and decoding preserves raw RGBA buffer fidelity', () => {
  const original = Buffer.alloc(16 * 16 * 4);
  for (let i = 0; i < original.length; i++) {
    original[i] = (i * 31) & 0xff;
  }

  const encoded = encodePNG(16, 16, original);
  assert.ok(Buffer.isBuffer(encoded));
  assert.equal(encoded[0], 0x89);
  assert.equal(encoded[1], 0x50);
  assert.equal(encoded[2], 0x4e);
  assert.equal(encoded[3], 0x47);

  const decoded = decodePNG(encoded);
  assert.equal(decoded.width, 16);
  assert.equal(decoded.height, 16);
  assert.ok(original.equals(decoded.data));
});

test('recolorToRuby processes PNG buffer and returns valid 16x16 PNG buffer', async () => {
  const diamondSwordPng = VANILLA_DIAMOND_TOOLS.sword();
  const rubySwordPng = await recolorToRuby(diamondSwordPng);

  assert.ok(Buffer.isBuffer(rubySwordPng));
  assert.equal(rubySwordPng[0], 0x89);
  assert.equal(rubySwordPng[1], 0x50);

  const decoded = decodePNG(rubySwordPng);
  assert.equal(decoded.width, 16);
  assert.equal(decoded.height, 16);
});

test('recolorToRuby processes raw RGBA buffer and returns raw buffer when requested', async () => {
  const rawInput = Buffer.alloc(16 * 16 * 4);
  for (let i = 0; i < 16 * 16; i++) {
    rawInput[i * 4] = 45;
    rawInput[i * 4 + 1] = 194;
    rawInput[i * 4 + 2] = 191;
    rawInput[i * 4 + 3] = 255;
  }

  const rawOutput = await recolorToRuby(rawInput, { format: 'raw', width: 16, height: 16 });
  assert.ok(Buffer.isBuffer(rawOutput));
  assert.equal(rawOutput.length, 1024);
  assert.equal(rawOutput[0], 196);
  assert.equal(rawOutput[1], 35);
  assert.equal(rawOutput[2], 60);
  assert.equal(rawOutput[3], 255);
});

test('generateRubyToolsets generates all five vanilla tools with diamond and ruby variants', async () => {
  const results = await generateRubyToolsets();
  const expectedTools = ['pickaxe', 'sword', 'axe', 'shovel', 'hoe'];

  for (const name of expectedTools) {
    assert.ok(results[name], `Missing tool ${name}`);
    assert.ok(Buffer.isBuffer(results[name].diamond));
    assert.ok(Buffer.isBuffer(results[name].ruby));

    const decodedDiamond = decodePNG(results[name].diamond);
    const decodedRuby = decodePNG(results[name].ruby);

    assert.equal(decodedDiamond.width, 16);
    assert.equal(decodedDiamond.height, 16);
    assert.equal(decodedRuby.width, 16);
    assert.equal(decodedRuby.height, 16);
  }
});

test('recolorPixel produces hue shifting rather than flat monochrome multiplier', () => {
  const highlight = recolorPixel(188, 252, 252, 255);
  const midtone = recolorPixel(45, 194, 191, 255);
  const shadow = recolorPixel(32, 139, 139, 255);

  const highlightRatioGtoR = highlight[1] / highlight[0];
  const midtoneRatioGtoR = midtone[1] / midtone[0];
  const shadowRatioGtoR = shadow[1] / shadow[0];

  assert.ok(highlightRatioGtoR > 0.70);
  assert.ok(midtoneRatioGtoR < 0.30);
  assert.ok(shadowRatioGtoR < 0.25);
});

test('recolorToRuby rejects non-buffer inputs with TypeError', async () => {
  await assert.rejects(
    async () => {
      await recolorToRuby('invalid_string');
    },
    {
      name: 'TypeError'
    }
  );
});
