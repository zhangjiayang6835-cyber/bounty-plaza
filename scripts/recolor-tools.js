// scripts/recolor-tools.js
// Node.js script to generate Ruby‑colored tool textures from vanilla diamond textures.
// Uses the Sharp library to apply hue rotation, saturation boost, and subtle brightness
// adjustments while preserving the original alpha channel and shading details.

import sharp from 'sharp';
import { promises as fs } from 'fs';
import path from 'path';

/**
 * Recolor a 16×16 diamond tool texture to a Ruby variant.
 *
 * The algorithm performs three main steps:
 *   1. Convert the image to the HSL colour space.
 *   2. Rotate the hue towards ruby red (≈ 0°), increase saturation, and slightly
 *      boost brightness to retain depth.
 *   3. Preserve the original alpha channel so transparent pixels remain crisp.
 *
 * This approach keeps the original shading and specular highlights because the
 * colour transformation is applied uniformly across the image rather than a
 * flat RGB multiplication.
 *
 * @param {Buffer} inputBuffer - Raw PNG data of the diamond tool texture.
 * @returns {Promise<Buffer>} - PNG data of the recoloured Ruby texture.
 */
export async function recolorToRuby(inputBuffer) {
  // Sharp works in the sRGB colour space by default.
  // `modulate` allows hue rotation (degrees), saturation, and brightness scaling.
  // Ruby red is roughly hue 0° (or 360°). Diamond textures are typically a light
  // blue; rotating the hue by -180° brings the colour into the red spectrum.
  const hueShift = -180; // degrees
  const saturation = 1.8; // 80% more saturated
  const brightness = 1.1; // 10% brighter to keep depth

  const image = sharp(inputBuffer)
    .ensureAlpha() // guarantee an alpha channel for proper masking
    .modulate({ hue: hueShift, saturation, brightness })
    .png(); // output as PNG to keep transparency

  return await image.toBuffer();
}

/**
 * Simple CLI wrapper.
 * Usage: node recolor-tools.js <input.png> <output.png>
 */
async function main() {
  const [, , inputPath, outputPath] = process.argv;
  if (!inputPath || !outputPath) {
    console.error('Usage: node recolor-tools.js <input.png> <output.png>');
    process.exit(1);
  }

  try {
    const inputBuffer = await fs.readFile(path.resolve(inputPath));
    const outputBuffer = await recolorToRuby(inputBuffer);
    await fs.writeFile(path.resolve(outputPath), outputBuffer);
    console.log(`Ruby texture written to ${outputPath}`);
  } catch (err) {
    console.error('Error processing texture:', err.message);
    process.exit(1);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  // When executed directly via `node recolor-tools.js`
  main();
}
