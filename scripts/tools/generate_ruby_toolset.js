#!/usr/bin/env node
/**
 * @fileoverview Deterministic Node.js CLI script that generates ruby toolset textures from diamond textures.
 */

import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';

/**
 * Canonical fallback Base64 encoded vanilla 16x16 diamond textures.
 */
export const CANONICAL_DIAMOND_BASE64 = {
  sword: 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAJFBMVEUAAAAOPzYIJSAz68uk/fArx6weincVY1VoTh5JNhUoHguJZycazUdMAAAAAXRSTlMAQObYZgAAAExJREFUGNN1jsENwDAMAgGndpLuv29/jZFa/+4QwkA/ks5jyPky8cHxwyQAxslZNAaYiux9Zlb4A0XjNcVu1r0hvYacGwB0Rq0OSC4ehwkBE0lygnsAAAAASUVORK5CYII=',
  pickaxe: 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQBAMAAADt3eJSAAAAHlBMVEUAAAAz68srx6wnspqJZydoTh5JNhUOPzYoHgsIJSBDqdTeAAAAAXRSTlMAQObYZgAAAEZJREFUeNpjwArKywvANLuQsXoqmFU509iDAQKSLCE0W4TRBDAjpWHyBIgAw+QJEAGGSRMgAgwTJ0AEGDihAlAtUEYHms0AO88PQ5cytswAAAAASUVORK5CYII=',
  axe: 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQBAMAAADt3eJSAAAAIVBMVEUAAAAz68srx6wnspqJZyceindoTh5JNhUOPzYoHgsIJSBnmo+OAAAAAXRSTlMAQObYZgAAAEBJREFUeNpjQAEcDVBGowRUQFgDKmBsngBmLFQOngBmcC03tYLIlU2GMNg9uRZABCYwQAQyGSCgBJcAw0wGVAAAdKIMO6K/xjAAAAAASUVORK5CYII=',
  shovel: 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAHlBMVEUAAABJNhUoHgsz68sIJSAOPzaJZycrx6wnsppoTh6NJ1OoAAAAAXRSTlMAQObYZgAAADhJREFUGFeVyTkCACAMAkFyqv//sG3Ayu0GgJ+qkh2x51KxdiR7zQGmbleDfBwzazH/9vxiwHWgLn4QANVOSXqPAAAAAElFTkSuQmCC',
  hoe: 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQBAMAAADt3eJSAAAAHlBMVEUAAAAz68srx6wnspqJZydoTh5JNhUOPzYoHgsIJSBDqdTeAAAAAXRSTlMAQObYZgAAADFJREFUeNpjQAbs5VBGoVIBhME5WT0VyjL2YICAJEsIzRYxAcJIaYAJMJAqwNDBgAoA50AJ6TlXpBwAAAAASUVORK5CYII='
};

/**
 * Standard toolset item names.
 */
export const TOOLSET_ITEMS = ['sword', 'pickaxe', 'axe', 'shovel', 'hoe'];

/**
 * Computes standard CRC32 checksum for PNG chunk verification.
 * @param {Buffer} buffer - Buffer to compute checksum for.
 * @returns {number} 32-bit unsigned integer checksum.
 */
export function calculateCrc32(buffer) {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let current = i;
    for (let bit = 0; bit < 8; bit++) {
      current = (current & 1) ? (0xedb88320 ^ (current >>> 1)) : (current >>> 1);
    }
    table[i] = current >>> 0;
  }

  let crc = 0 ^ (-1);
  for (let index = 0; index < buffer.length; index++) {
    crc = (crc >>> 8) ^ table[(crc ^ buffer[index]) & 0xff];
  }
  return (crc ^ (-1)) >>> 0;
}

/**
 * Packages data into a standard PNG chunk.
 * @param {string} type - 4-character ASCII chunk type.
 * @param {Buffer} data - Binary payload of the chunk.
 * @returns {Buffer} Formatted chunk buffer.
 */
export function createPngChunk(type, data) {
  const lengthBuffer = Buffer.alloc(4);
  lengthBuffer.writeUInt32BE(data.length, 0);

  const typeBuffer = Buffer.from(type, 'ascii');
  const crcTarget = Buffer.concat([typeBuffer, data]);

  const crcBuffer = Buffer.alloc(4);
  crcBuffer.writeUInt32BE(calculateCrc32(crcTarget), 0);

  return Buffer.concat([lengthBuffer, typeBuffer, data, crcBuffer]);
}

/**
 * Implements the Paeth predictor filter algorithm for PNG decoding.
 * @param {number} left - Left pixel byte.
 * @param {number} above - Above pixel byte.
 * @param {number} upperLeft - Upper-left pixel byte.
 * @returns {number} Predicted byte value.
 */
export function paethPredictor(left, above, upperLeft) {
  const baseEstimate = left + above - upperLeft;
  const distanceLeft = Math.abs(baseEstimate - left);
  const distanceAbove = Math.abs(baseEstimate - above);
  const distanceUpperLeft = Math.abs(baseEstimate - upperLeft);

  if (distanceLeft <= distanceAbove && distanceLeft <= distanceUpperLeft) {
    return left;
  }
  if (distanceAbove <= distanceUpperLeft) {
    return above;
  }
  return upperLeft;
}

/**
 * Decodes a PNG image buffer into a 2D matrix of RGBA pixels.
 * Supports Color Type 6 (RGBA), Type 2 (RGB), and Type 3 (Indexed with PLTE/tRNS).
 * @param {Buffer} buffer - Binary PNG file data.
 * @returns {{ width: number, height: number, pixels: Array<Array<{ r: number, g: number, b: number, a: number }>> }}
 */
export function decodePng(buffer) {
  const signature = buffer.subarray(0, 8);
  const validSignature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  if (!signature.equals(validSignature)) {
    throw new Error('Invalid PNG signature.');
  }

  let cursor = 8;
  let width = 0;
  let height = 0;
  let bitDepth = 8;
  let colorType = 6;
  const palette = [];
  const transparency = [];
  const idatChunks = [];

  while (cursor < buffer.length) {
    const chunkLength = buffer.readUInt32BE(cursor);
    const chunkType = buffer.toString('ascii', cursor + 4, cursor + 8);
    const chunkData = buffer.subarray(cursor + 8, cursor + 8 + chunkLength);
    cursor += 12 + chunkLength;

    if (chunkType === 'IHDR') {
      width = chunkData.readUInt32BE(0);
      height = chunkData.readUInt32BE(4);
      bitDepth = chunkData[8];
      colorType = chunkData[9];
    } else if (chunkType === 'PLTE') {
      for (let offset = 0; offset < chunkData.length; offset += 3) {
        palette.push({
          r: chunkData[offset],
          g: chunkData[offset + 1],
          b: chunkData[offset + 2]
        });
      }
    } else if (chunkType === 'tRNS') {
      for (let offset = 0; offset < chunkData.length; offset++) {
        transparency.push(chunkData[offset]);
      }
    } else if (chunkType === 'IDAT') {
      idatChunks.push(chunkData);
    } else if (chunkType === 'IEND') {
      break;
    }
  }

  const decompressedData = zlib.inflateSync(Buffer.concat(idatChunks));
  let bytesPerPixel = 4;
  if (colorType === 2) {
    bytesPerPixel = 3;
  } else if (colorType === 3) {
    bytesPerPixel = 1;
  }

  const stride = 1 + (colorType === 3 && bitDepth === 4 ? Math.ceil(width / 2) : width * bytesPerPixel);
  const pixelRows = [];
  let previousRawRow = Buffer.alloc(stride - 1);
  let readOffset = 0;

  for (let rowIndex = 0; rowIndex < height; rowIndex++) {
    const filterType = decompressedData[readOffset++];
    const filteredScanline = decompressedData.subarray(readOffset, readOffset + stride - 1);
    readOffset += stride - 1;

    const reconstructedScanline = Buffer.alloc(stride - 1);
    const step = colorType === 3 && bitDepth === 4 ? 1 : bytesPerPixel;

    for (let col = 0; col < filteredScanline.length; col++) {
      const rawByte = filteredScanline[col];
      const leftByte = col >= step ? reconstructedScanline[col - step] : 0;
      const aboveByte = previousRawRow[col];
      const upperLeftByte = col >= step ? previousRawRow[col - step] : 0;

      let unmaskedByte = 0;
      switch (filterType) {
        case 0:
          unmaskedByte = rawByte;
          break;
        case 1:
          unmaskedByte = (rawByte + leftByte) & 0xff;
          break;
        case 2:
          unmaskedByte = (rawByte + aboveByte) & 0xff;
          break;
        case 3:
          unmaskedByte = (rawByte + Math.floor((leftByte + aboveByte) / 2)) & 0xff;
          break;
        case 4:
          unmaskedByte = (rawByte + paethPredictor(leftByte, aboveByte, upperLeftByte)) & 0xff;
          break;
        default:
          unmaskedByte = rawByte;
      }
      reconstructedScanline[col] = unmaskedByte;
    }

    previousRawRow = reconstructedScanline;
    const rowPixels = [];

    if (colorType === 6) {
      for (let x = 0; x < width; x++) {
        const offset = x * 4;
        rowPixels.push({
          r: reconstructedScanline[offset],
          g: reconstructedScanline[offset + 1],
          b: reconstructedScanline[offset + 2],
          a: reconstructedScanline[offset + 3]
        });
      }
    } else if (colorType === 2) {
      for (let x = 0; x < width; x++) {
        const offset = x * 3;
        rowPixels.push({
          r: reconstructedScanline[offset],
          g: reconstructedScanline[offset + 1],
          b: reconstructedScanline[offset + 2],
          a: 255
        });
      }
    } else if (colorType === 3) {
      if (bitDepth === 4) {
        for (let x = 0; x < width; x++) {
          const byteIndex = Math.floor(x / 2);
          const paletteIndex = (x % 2 === 0)
            ? (reconstructedScanline[byteIndex] >> 4) & 0x0f
            : reconstructedScanline[byteIndex] & 0x0f;
          const entry = palette[paletteIndex] || { r: 0, g: 0, b: 0 };
          const alpha = transparency[paletteIndex] !== undefined ? transparency[paletteIndex] : 255;
          rowPixels.push({ r: entry.r, g: entry.g, b: entry.b, a: alpha });
        }
      } else {
        for (let x = 0; x < width; x++) {
          const paletteIndex = reconstructedScanline[x];
          const entry = palette[paletteIndex] || { r: 0, g: 0, b: 0 };
          const alpha = transparency[paletteIndex] !== undefined ? transparency[paletteIndex] : 255;
          rowPixels.push({ r: entry.r, g: entry.g, b: entry.b, a: alpha });
        }
      }
    }

    pixelRows.push(rowPixels);
  }

  return { width, height, pixels: pixelRows };
}

/**
 * Encodes a 2D matrix of RGBA pixels into a standardized 32-bit RGBA PNG buffer.
 * @param {number} width - Image width.
 * @param {number} height - Image height.
 * @param {Array<Array<{ r: number, g: number, b: number, a: number }>>} pixels - RGBA matrix.
 * @returns {Buffer} Formatted binary PNG buffer.
 */
export function encodePng(width, height, pixels) {
  const header = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(width, 0);
  ihdrData.writeUInt32BE(height, 4);
  ihdrData[8] = 8;
  ihdrData[9] = 6;
  ihdrData[10] = 0;
  ihdrData[11] = 0;
  ihdrData[12] = 0;

  const ihdrChunk = createPngChunk('IHDR', ihdrData);

  const scanlineLength = 1 + (width * 4);
  const rawImageBuffer = Buffer.alloc(scanlineLength * height);

  for (let y = 0; y < height; y++) {
    const rowOffset = y * scanlineLength;
    rawImageBuffer[rowOffset] = 0;
    for (let x = 0; x < width; x++) {
      const pixel = pixels[y][x];
      const pixelOffset = rowOffset + 1 + (x * 4);
      rawImageBuffer[pixelOffset] = pixel.r;
      rawImageBuffer[pixelOffset + 1] = pixel.g;
      rawImageBuffer[pixelOffset + 2] = pixel.b;
      rawImageBuffer[pixelOffset + 3] = pixel.a;
    }
  }

  const compressedData = zlib.deflateSync(rawImageBuffer, { level: 9 });
  const idatChunk = createPngChunk('IDAT', compressedData);
  const iendChunk = createPngChunk('IEND', Buffer.alloc(0));

  return Buffer.concat([header, ihdrChunk, idatChunk, iendChunk]);
}

/**
 * Converts RGB components to HSV color space.
 * @param {number} red - Red component [0, 255].
 * @param {number} green - Green component [0, 255].
 * @param {number} blue - Blue component [0, 255].
 * @returns {{ h: number, s: number, v: number }} Hue [0, 360), Saturation [0, 1], Value [0, 1].
 */
export function rgbToHsv(red, green, blue) {
  const normalizedRed = red / 255;
  const normalizedGreen = green / 255;
  const normalizedBlue = blue / 255;

  const maxVal = Math.max(normalizedRed, normalizedGreen, normalizedBlue);
  const minVal = Math.min(normalizedRed, normalizedGreen, normalizedBlue);
  const delta = maxVal - minVal;

  let hue = 0;
  const saturation = maxVal === 0 ? 0 : delta / maxVal;
  const value = maxVal;

  if (delta !== 0) {
    if (maxVal === normalizedRed) {
      hue = ((normalizedGreen - normalizedBlue) / delta) + (normalizedGreen < normalizedBlue ? 6 : 0);
    } else if (maxVal === normalizedGreen) {
      hue = ((normalizedBlue - normalizedRed) / delta) + 2;
    } else {
      hue = ((normalizedRed - normalizedGreen) / delta) + 4;
    }
    hue *= 60;
  }

  return { h: hue, s: saturation, v: value };
}

/**
 * Converts HSV components to RGB color space.
 * @param {number} hue - Hue angle [0, 360).
 * @param {number} saturation - Saturation [0, 1].
 * @param {number} value - Value [0, 1].
 * @returns {{ r: number, g: number, b: number }} Clamped RGB structure [0, 255].
 */
export function hsvToRgb(hue, saturation, value) {
  const normalizedHue = ((hue % 360) + 360) % 360;
  const sector = Math.floor(normalizedHue / 60) % 6;
  const fractionalSector = (normalizedHue / 60) - Math.floor(normalizedHue / 60);

  const primaryValue = value;
  const secondaryValueP = value * (1 - saturation);
  const secondaryValueQ = value * (1 - (fractionalSector * saturation));
  const secondaryValueT = value * (1 - ((1 - fractionalSector) * saturation));

  let redComponent = 0;
  let greenComponent = 0;
  let blueComponent = 0;

  switch (sector) {
    case 0:
      redComponent = primaryValue;
      greenComponent = secondaryValueT;
      blueComponent = secondaryValueP;
      break;
    case 1:
      redComponent = secondaryValueQ;
      greenComponent = primaryValue;
      blueComponent = secondaryValueP;
      break;
    case 2:
      redComponent = secondaryValueP;
      greenComponent = primaryValue;
      blueComponent = secondaryValueT;
      break;
    case 3:
      redComponent = secondaryValueP;
      greenComponent = secondaryValueQ;
      blueComponent = primaryValue;
      break;
    case 4:
      redComponent = secondaryValueT;
      greenComponent = secondaryValueP;
      blueComponent = primaryValue;
      break;
    case 5:
      redComponent = primaryValue;
      greenComponent = secondaryValueP;
      blueComponent = secondaryValueQ;
      break;
    default:
      redComponent = primaryValue;
      greenComponent = secondaryValueP;
      blueComponent = secondaryValueQ;
  }

  return {
    r: Math.min(255, Math.max(0, Math.round(redComponent * 255))),
    g: Math.min(255, Math.max(0, Math.round(greenComponent * 255))),
    b: Math.min(255, Math.max(0, Math.round(blueComponent * 255)))
  };
}

/**
 * Identifies whether a given HSV color represents a diamond tool component.
 * Cyan-blue diamond hues range from 150 deg to 230 deg with non-zero saturation.
 * @param {number} hue - Hue angle.
 * @param {number} saturation - Saturation value.
 * @param {number} value - Value component.
 * @returns {boolean} True if the color belongs to diamond geometry.
 */
export function isDiamondColor(hue, saturation, value) {
  return hue >= 150 && hue <= 230 && saturation >= 0.15 && value >= 0.05;
}

/**
 * Shifts a single pixel from diamond palette to authentic ruby red.
 * Preserves full transparency for outer pixels, leaves handle/wood pixels untouched,
 * and maintains continuous Jappa hand-shaded depth gradations.
 * @param {{ r: number, g: number, b: number, a: number }} pixel - Source pixel.
 * @param {{ targetHue?: number }} [options] - Conversion options.
 * @returns {{ r: number, g: number, b: number, a: number }} Transformed pixel.
 */
export function shiftPixelToRuby(pixel, options = {}) {
  if (pixel.a === 0) {
    return { r: 0, g: 0, b: 0, a: 0 };
  }

  const { h, s, v } = rgbToHsv(pixel.r, pixel.g, pixel.b);
  if (!isDiamondColor(h, s, v)) {
    return { r: pixel.r, g: pixel.g, b: pixel.b, a: pixel.a };
  }

  const baseTargetHue = options.targetHue ?? 352;
  const temperatureShift = (v - 0.5) * 6;
  const computedHue = (baseTargetHue + temperatureShift + 360) % 360;

  const transformedRgb = hsvToRgb(computedHue, s, v);
  return {
    r: transformedRgb.r,
    g: transformedRgb.g,
    b: transformedRgb.b,
    a: pixel.a
  };
}

/**
 * Transforms an input PNG image buffer of a diamond tool into ruby red.
 * @param {Buffer} inputPngBuffer - Source PNG binary buffer.
 * @param {{ targetHue?: number }} [options] - Color grading options.
 * @returns {Buffer} Resulting 16x16 RGBA PNG binary buffer.
 */
export function generateRubyTexture(inputPngBuffer, options = {}) {
  const decoded = decodePng(inputPngBuffer);
  const transformedPixels = decoded.pixels.map((row) =>
    row.map((pixel) => shiftPixelToRuby(pixel, options))
  );
  return encodePng(decoded.width, decoded.height, transformedPixels);
}

/**
 * Generates the full set of ruby toolset textures from diamond counterparts.
 * @param {object} [options] - Generator options.
 * @param {string} [options.inputDir] - Source directory for diamond textures.
 * @param {string} [options.outputDir] - Destination directory for ruby textures.
 * @param {Array<string>} [options.items] - List of tool items to generate.
 * @param {number} [options.targetHue] - Target ruby hue angle.
 * @returns {Promise<Array<{ item: string, outputPath: string, size: number }>>} Generated file metadata.
 */
export async function generateRubyToolset(options = {}) {
  const inputDir = options.inputDir ? path.resolve(options.inputDir) : path.resolve('textures/items');
  const outputDir = options.outputDir ? path.resolve(options.outputDir) : path.resolve('textures/items');
  const items = options.items || TOOLSET_ITEMS;

  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const generatedResults = [];

  for (const item of items) {
    const candidateInputPath = path.join(inputDir, `diamond_${item}.png`);
    let inputBuffer = null;

    if (fs.existsSync(candidateInputPath)) {
      inputBuffer = fs.readFileSync(candidateInputPath);
    } else if (CANONICAL_DIAMOND_BASE64[item]) {
      inputBuffer = Buffer.from(CANONICAL_DIAMOND_BASE64[item], 'base64');
    } else {
      throw new Error(`Missing source diamond texture for item: ${item}`);
    }

    const outputBuffer = generateRubyTexture(inputBuffer, { targetHue: options.targetHue });
    const outputPath = path.join(outputDir, `ruby_${item}.png`);
    fs.writeFileSync(outputPath, outputBuffer);

    generatedResults.push({
      item,
      outputPath,
      size: outputBuffer.length
    });
  }

  return generatedResults;
}

/**
 * Parses CLI command-line arguments into an options dictionary.
 * @param {Array<string>} args - Command-line arguments.
 * @returns {object} Options dictionary.
 */
export function parseCommandLineArgs(args) {
  const options = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--input-dir' && args[i + 1]) {
      options.inputDir = args[++i];
    } else if (args[i] === '--output-dir' && args[i + 1]) {
      options.outputDir = args[++i];
    } else if (args[i] === '--target-hue' && args[i + 1]) {
      options.targetHue = parseFloat(args[++i]);
    } else if (args[i] === '--items' && args[i + 1]) {
      options.items = args[++i].split(',').map((item) => item.trim());
    }
  }
  return options;
}

const currentModulePath = fileURLToPath(import.meta.url);
const invokedScriptPath = process.argv[1] ? path.resolve(process.argv[1]) : '';

if (invokedScriptPath === currentModulePath) {
  const parsedOptions = parseCommandLineArgs(process.argv.slice(2));
  generateRubyToolset(parsedOptions)
    .then((results) => {
      process.stdout.write(`Generated ${results.length} ruby toolset textures.\n`);
      for (const entry of results) {
        process.stdout.write(`- ${entry.item}: ${entry.outputPath} (${entry.size} bytes)\n`);
      }
    })
    .catch((error) => {
      process.stderr.write(`Execution failed: ${error.message}\n`);
      process.exit(1);
    });
}
