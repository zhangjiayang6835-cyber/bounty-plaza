const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

let crcTableCache = null;

/**
 * Generates and caches the 32-bit CRC lookup table.
 *
 * @returns {Uint32Array} The initialized CRC32 lookup table.
 */
function getCrcTable() {
  if (!crcTableCache) {
    const table = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) {
        c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
      }
      table[n] = c >>> 0;
    }
    crcTableCache = table;
  }
  return crcTableCache;
}

/**
 * Computes the CRC32 checksum for a given buffer.
 *
 * @param {Buffer} buf Input buffer to calculate checksum for.
 * @returns {number} 32-bit unsigned integer CRC32 checksum.
 */
function computeCrc32(buf) {
  const table = getCrcTable();
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) {
    c = table[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

/**
 * Constructs a binary PNG chunk consisting of length, type, payload, and CRC32.
 *
 * @param {string} type Four-character ASCII chunk type.
 * @param {Buffer} data Chunk binary payload.
 * @returns {Buffer} Formatted chunk buffer.
 */
function createPngChunk(type, data) {
  const typeBuf = Buffer.from(type, 'ascii');
  const lenBuf = Buffer.alloc(4);
  lenBuf.writeUInt32BE(data.length, 0);
  const typeAndData = Buffer.concat([typeBuf, data]);
  const crcBuf = Buffer.alloc(4);
  crcBuf.writeUInt32BE(computeCrc32(typeAndData), 0);
  return Buffer.concat([lenBuf, typeAndData, crcBuf]);
}

/**
 * Computes the Paeth filter predictor for PNG reconstruction.
 *
 * @param {number} a Left byte value.
 * @param {number} b Above byte value.
 * @param {number} c Upper-left byte value.
 * @returns {number} Selected predictor byte value.
 */
function paethPredictor(a, b, c) {
  const p = a + b - c;
  const pa = Math.abs(p - a);
  const pb = Math.abs(p - b);
  const pc = Math.abs(p - c);
  if (pa <= pb && pa <= pc) return a;
  if (pb <= pc) return b;
  return c;
}

/**
 * Decodes an input PNG buffer into raw uncompressed RGBA pixel data.
 *
 * @param {Buffer} buf Raw PNG binary buffer.
 * @returns {{ width: number, height: number, data: Buffer }} Decoded dimensions and raw RGBA pixel buffer.
 */
function decodePNG(buf) {
  if (!buf || buf.length < 8) {
    throw new Error('Buffer too small for PNG decoding');
  }
  if (buf[0] !== 0x89 || buf[1] !== 0x50 || buf[2] !== 0x4e || buf[3] !== 0x47 ||
      buf[4] !== 0x0d || buf[5] !== 0x0a || buf[6] !== 0x1a || buf[7] !== 0x0a) {
    throw new Error('Invalid PNG signature');
  }

  let offset = 8;
  let width = 0;
  let height = 0;
  let colorType = 6;
  const idatChunks = [];

  while (offset + 8 <= buf.length) {
    const chunkLen = buf.readUInt32BE(offset);
    const chunkType = buf.toString('ascii', offset + 4, offset + 8);
    const chunkData = buf.slice(offset + 8, offset + 8 + chunkLen);
    offset += 12 + chunkLen;

    if (chunkType === 'IHDR') {
      width = chunkData.readUInt32BE(0);
      height = chunkData.readUInt32BE(4);
      colorType = chunkData[9];
    } else if (chunkType === 'IDAT') {
      idatChunks.push(chunkData);
    } else if (chunkType === 'IEND') {
      break;
    }
  }

  if (!width || !height) {
    throw new Error('Missing or corrupt IHDR chunk in PNG');
  }

  const inflated = zlib.inflateSync(Buffer.concat(idatChunks));
  const bytesPerPixel = (colorType === 6) ? 4 : ((colorType === 2) ? 3 : 4);
  const scanlineLength = 1 + width * bytesPerPixel;
  const rawRgba = Buffer.alloc(width * height * 4);

  let prevScanline = Buffer.alloc(width * bytesPerPixel);
  for (let y = 0; y < height; y++) {
    const filterType = inflated[y * scanlineLength];
    const currentLine = Buffer.alloc(width * bytesPerPixel);
    const lineDataOffset = y * scanlineLength + 1;

    for (let x = 0; x < width * bytesPerPixel; x++) {
      const byte = inflated[lineDataOffset + x];
      const left = x >= bytesPerPixel ? currentLine[x - bytesPerPixel] : 0;
      const up = prevScanline[x];
      const upLeft = x >= bytesPerPixel ? prevScanline[x - bytesPerPixel] : 0;

      let val = 0;
      if (filterType === 0) {
        val = byte;
      } else if (filterType === 1) {
        val = (byte + left) & 0xff;
      } else if (filterType === 2) {
        val = (byte + up) & 0xff;
      } else if (filterType === 3) {
        val = (byte + Math.floor((left + up) / 2)) & 0xff;
      } else if (filterType === 4) {
        val = (byte + paethPredictor(left, up, upLeft)) & 0xff;
      } else {
        val = byte;
      }
      currentLine[x] = val;
    }

    if (colorType === 6) {
      currentLine.copy(rawRgba, y * width * 4);
    } else if (colorType === 2) {
      for (let px = 0; px < width; px++) {
        rawRgba[y * width * 4 + px * 4] = currentLine[px * 3];
        rawRgba[y * width * 4 + px * 4 + 1] = currentLine[px * 3 + 1];
        rawRgba[y * width * 4 + px * 4 + 2] = currentLine[px * 3 + 2];
        rawRgba[y * width * 4 + px * 4 + 3] = 255;
      }
    }
    prevScanline = currentLine;
  }

  return { width, height, data: rawRgba };
}

/**
 * Encodes raw uncompressed RGBA pixel data into a valid PNG buffer.
 *
 * @param {number} width Image width in pixels.
 * @param {number} height Image height in pixels.
 * @param {Buffer} rgbaBuffer Raw RGBA buffer of size width * height * 4.
 * @returns {Buffer} Formatted binary PNG buffer.
 */
function encodePNG(width, height, rgbaBuffer) {
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(width, 0);
  ihdrData.writeUInt32BE(height, 4);
  ihdrData[8] = 8;
  ihdrData[9] = 6;
  ihdrData[10] = 0;
  ihdrData[11] = 0;
  ihdrData[12] = 0;
  const ihdrChunk = createPngChunk('IHDR', ihdrData);

  const rawScanlines = Buffer.alloc(height * (1 + width * 4));
  for (let y = 0; y < height; y++) {
    rawScanlines[y * (1 + width * 4)] = 0;
    rgbaBuffer.copy(rawScanlines, y * (1 + width * 4) + 1, y * width * 4, (y + 1) * width * 4);
  }

  const idatChunk = createPngChunk('IDAT', zlib.deflateSync(rawScanlines, { level: 9 }));
  const iendChunk = createPngChunk('IEND', Buffer.alloc(0));
  return Buffer.concat([signature, ihdrChunk, idatChunk, iendChunk]);
}

const PALETTE_MAP = [
  { match: [188, 252, 252], replace: [255, 205, 218] },
  { match: [155, 244, 242], replace: [255, 185, 195] },
  { match: [95, 234, 201],  replace: [247, 92, 116] },
  { match: [74, 237, 217],  replace: [240, 73, 96] },
  { match: [45, 194, 191],  replace: [196, 35, 60] },
  { match: [32, 139, 139],  replace: [140, 19, 40] },
  { match: [25, 95, 95],    replace: [84, 9, 23] },
  { match: [17, 57, 54],    replace: [48, 5, 13] }
];

/**
 * Evaluates the weighted perceptual color distance between two RGB triplets.
 *
 * @param {number} r1 Red component of color 1.
 * @param {number} g1 Green component of color 1.
 * @param {number} b1 Blue component of color 1.
 * @param {number} r2 Red component of color 2.
 * @param {number} g2 Green component of color 2.
 * @param {number} b2 Blue component of color 2.
 * @returns {number} Weighted Euclidean perceptual distance.
 */
function colorDistance(r1, g1, b1, r2, g2, b2) {
  return Math.sqrt(2 * (r1 - r2) ** 2 + 4 * (g1 - g2) ** 2 + 3 * (b1 - b2) ** 2);
}

/**
 * Determines whether an RGBA pixel belongs to the diamond mineral family.
 *
 * @param {number} r Red channel value.
 * @param {number} g Green channel value.
 * @param {number} b Blue channel value.
 * @param {number} a Alpha channel value.
 * @returns {boolean} True if pixel is diamond material.
 */
function isDiamondMaterial(r, g, b, a) {
  if (a < 10) return false;
  if (r > g + 15 && r > b + 20) return false;

  const cyanDominant = (b > r + 15 && g > r + 10 && (g + b) > 65);
  const brightCyan = (b > 100 && g > 100 && r < 165 && (g + b) / 2 > r + 20);

  if (cyanDominant || brightCyan) return true;

  for (const entry of PALETTE_MAP) {
    const dist = colorDistance(r, g, b, entry.match[0], entry.match[1], entry.match[2]);
    if (dist < 45) return true;
  }

  return false;
}

/**
 * Evaluates continuous hue-shifted Ruby interpolation based on relative luminance.
 *
 * @param {number} lightness Normalized relative luminance between 0 and 1.
 * @returns {number[]} Array of three integers representing red, green, and blue.
 */
function interpolateRubyRamp(lightness) {
  const clamped = Math.max(0, Math.min(1, lightness));

  if (clamped >= 0.85) {
    const factor = (clamped - 0.85) / 0.15;
    return [
      255,
      Math.round(185 + factor * 70),
      Math.round(195 + factor * 60)
    ];
  }

  if (clamped >= 0.60) {
    const factor = (clamped - 0.60) / 0.25;
    return [
      Math.round(240 + factor * 15),
      Math.round(73 + factor * 112),
      Math.round(96 + factor * 99)
    ];
  }

  if (clamped >= 0.40) {
    const factor = (clamped - 0.40) / 0.20;
    return [
      Math.round(196 + factor * 44),
      Math.round(35 + factor * 38),
      Math.round(60 + factor * 36)
    ];
  }

  if (clamped >= 0.20) {
    const factor = (clamped - 0.20) / 0.20;
    return [
      Math.round(140 + factor * 56),
      Math.round(19 + factor * 16),
      Math.round(40 + factor * 20)
    ];
  }

  if (clamped >= 0.10) {
    const factor = (clamped - 0.10) / 0.10;
    return [
      Math.round(84 + factor * 56),
      Math.round(9 + factor * 10),
      Math.round(23 + factor * 17)
    ];
  }

  const factor = clamped / 0.10;
  return [
    Math.round(48 + factor * 36),
    Math.round(5 + factor * 4),
    Math.round(13 + factor * 10)
  ];
}

/**
 * Programmatically recolors a single RGBA pixel into an authentic Jappa-style Ruby pixel.
 *
 * @param {number} r Red channel value (0-255).
 * @param {number} g Green channel value (0-255).
 * @param {number} b Blue channel value (0-255).
 * @param {number} a Alpha channel value (0-255).
 * @returns {number[]} Four-element array [r, g, b, a].
 */
function recolorPixel(r, g, b, a) {
  if (a < 10) {
    return [r, g, b, a];
  }

  if (!isDiamondMaterial(r, g, b, a)) {
    return [r, g, b, a];
  }

  let closestEntry = null;
  let minDistance = Infinity;

  for (const entry of PALETTE_MAP) {
    const dist = colorDistance(r, g, b, entry.match[0], entry.match[1], entry.match[2]);
    if (dist < minDistance) {
      minDistance = dist;
      closestEntry = entry;
    }
  }

  if (minDistance <= 18 && closestEntry) {
    return [closestEntry.replace[0], closestEntry.replace[1], closestEntry.replace[2], a];
  }

  const relativeLuminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  const rampColor = interpolateRubyRamp(relativeLuminance);

  return [rampColor[0], rampColor[1], rampColor[2], a];
}

/**
 * Recolors an uncompressed RGBA byte buffer.
 *
 * @param {Buffer} rgbaBuffer Input buffer containing raw RGBA pixel data.
 * @param {number} width Image width in pixels.
 * @param {number} height Image height in pixels.
 * @returns {Buffer} Recolored uncompressed RGBA buffer.
 */
function recolorRawBuffer(rgbaBuffer, width, height) {
  const output = Buffer.alloc(width * height * 4);
  const totalPixels = width * height;

  for (let i = 0; i < totalPixels; i++) {
    const idx = i * 4;
    const r = rgbaBuffer[idx];
    const g = rgbaBuffer[idx + 1];
    const b = rgbaBuffer[idx + 2];
    const a = rgbaBuffer[idx + 3];

    const [outR, outG, outB, outA] = recolorPixel(r, g, b, a);
    output[idx] = outR;
    output[idx + 1] = outG;
    output[idx + 2] = outB;
    output[idx + 3] = outA;
  }

  return output;
}

/**
 * Main public entrypoint to recolor a diamond texture into an authentic Jappa Ruby texture.
 *
 * @param {Buffer} inputBuffer Buffer containing a PNG image or raw RGBA bytes.
 * @param {Object} [options] Optional configuration flags.
 * @returns {Promise<Buffer>} Buffer containing the recolored PNG image.
 */
async function recolorToRuby(inputBuffer, options = {}) {
  if (!Buffer.isBuffer(inputBuffer)) {
    throw new TypeError('inputBuffer must be an instance of Buffer');
  }

  let width = options.width || 16;
  let height = options.height || 16;
  let rawData = null;

  if (inputBuffer.length >= 8 &&
      inputBuffer[0] === 0x89 && inputBuffer[1] === 0x50 &&
      inputBuffer[2] === 0x4e && inputBuffer[3] === 0x47) {
    const decoded = decodePNG(inputBuffer);
    width = decoded.width;
    height = decoded.height;
    rawData = decoded.data;
  } else if (inputBuffer.length === width * height * 4) {
    rawData = inputBuffer;
  } else {
    throw new Error(`Unrecognized input buffer format with byte length: ${inputBuffer.length}`);
  }

  const recoloredRaw = recolorRawBuffer(rawData, width, height);

  if (options.format === 'raw') {
    return recoloredRaw;
  }

  return encodePNG(width, height, recoloredRaw);
}

const VANILLA_PALETTE = {
  0: [0, 0, 0, 0],
  1: [188, 252, 252, 255],
  2: [74, 237, 217, 255],
  3: [45, 194, 191, 255],
  4: [32, 139, 139, 255],
  5: [25, 95, 95, 255],
  6: [17, 57, 54, 255],
  7: [143, 103, 60, 255],
  8: [110, 77, 37, 255],
  9: [75, 49, 20, 255],
  10: [46, 29, 12, 255]
};

const DIAMOND_SWORD_GRID = [
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 1, 5],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 1, 5],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 3, 4, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 3, 4, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 3, 4, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 3, 4, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 5, 2, 3, 4, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 5, 2, 3, 4, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 5, 5, 2, 3, 4, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 5, 7, 8, 5, 4, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 5, 8, 9, 8, 5, 5, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 5, 8, 9, 8, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [5, 8, 9, 8, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [5, 9, 10, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 5, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
];

const DIAMOND_PICKAXE_GRID = [
  [0, 0, 0, 0, 5, 5, 5, 5, 5, 5, 5, 5, 0, 0, 0, 0],
  [0, 0, 0, 5, 1, 1, 2, 2, 2, 3, 3, 4, 5, 0, 0, 0],
  [0, 0, 5, 1, 2, 3, 3, 3, 4, 4, 4, 4, 5, 5, 0, 0],
  [0, 5, 1, 2, 3, 5, 5, 7, 5, 5, 4, 5, 2, 1, 5, 0],
  [5, 1, 2, 5, 5, 0, 0, 8, 0, 0, 5, 5, 3, 2, 1, 5],
  [5, 2, 5, 0, 0, 0, 8, 9, 8, 0, 0, 0, 5, 3, 2, 5],
  [5, 5, 0, 0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 5, 5, 0],
  [0, 0, 0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
];

const DIAMOND_AXE_GRID = [
  [0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 5, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 5, 1, 1, 2, 2, 3, 5, 0, 0, 0, 0],
  [0, 0, 0, 0, 5, 1, 2, 3, 3, 4, 4, 3, 5, 0, 0, 0],
  [0, 0, 0, 5, 1, 2, 3, 5, 7, 5, 4, 3, 2, 5, 0, 0],
  [0, 0, 0, 5, 2, 3, 4, 5, 8, 5, 5, 4, 3, 5, 0, 0],
  [0, 0, 0, 0, 5, 4, 5, 8, 9, 8, 5, 5, 5, 0, 0, 0],
  [0, 0, 0, 0, 0, 5, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
];

const DIAMOND_SHOVEL_GRID = [
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 1, 1, 2, 5],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 1, 2, 3, 3, 5],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 3, 4, 4, 5, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 3, 4, 5, 5, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 5, 5, 4, 5, 5, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 8, 9, 8, 5, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
];

const DIAMOND_HOE_GRID = [
  [0, 0, 0, 0, 0, 5, 5, 5, 5, 5, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 5, 1, 1, 2, 2, 3, 5, 0, 0, 0, 0, 0],
  [0, 0, 0, 5, 1, 2, 3, 4, 4, 3, 5, 0, 0, 0, 0, 0],
  [0, 0, 5, 2, 3, 5, 5, 7, 5, 4, 5, 0, 0, 0, 0, 0],
  [0, 5, 3, 4, 5, 0, 0, 8, 0, 5, 5, 0, 0, 0, 0, 0],
  [5, 4, 5, 5, 0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0],
  [5, 5, 0, 0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [8, 9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [9, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
];

/**
 * Builds a raw uncompressed RGBA buffer from a 16x16 indexed color grid.
 *
 * @param {number[][]} grid 16x16 matrix of color indices.
 * @returns {Buffer} 1024-byte RGBA buffer.
 */
function gridToRgbaBuffer(grid) {
  const buf = Buffer.alloc(16 * 16 * 4);
  for (let y = 0; y < 16; y++) {
    for (let x = 0; x < 16; x++) {
      const idx = (y * 16 + x) * 4;
      const paletteId = grid[y][x];
      const color = VANILLA_PALETTE[paletteId] || [0, 0, 0, 0];
      buf[idx] = color[0];
      buf[idx + 1] = color[1];
      buf[idx + 2] = color[2];
      buf[idx + 3] = color[3];
    }
  }
  return buf;
}

const VANILLA_DIAMOND_TOOLS = {
  sword: () => encodePNG(16, 16, gridToRgbaBuffer(DIAMOND_SWORD_GRID)),
  pickaxe: () => encodePNG(16, 16, gridToRgbaBuffer(DIAMOND_PICKAXE_GRID)),
  axe: () => encodePNG(16, 16, gridToRgbaBuffer(DIAMOND_AXE_GRID)),
  shovel: () => encodePNG(16, 16, gridToRgbaBuffer(DIAMOND_SHOVEL_GRID)),
  hoe: () => encodePNG(16, 16, gridToRgbaBuffer(DIAMOND_HOE_GRID))
};

/**
 * Batch generates all vanilla diamond tool textures and their Jappa Ruby variants.
 *
 * @param {string} [outputDir] Target output directory for PNG assets.
 * @returns {Promise<Object.<string, { diamond: Buffer, ruby: Buffer }>>} Map of generated tool buffers.
 */
async function generateRubyToolsets(outputDir) {
  const results = {};
  const toolNames = ['pickaxe', 'sword', 'axe', 'shovel', 'hoe'];

  if (outputDir) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  for (const name of toolNames) {
    const diamondBuffer = VANILLA_DIAMOND_TOOLS[name]();
    const rubyBuffer = await recolorToRuby(diamondBuffer);

    results[name] = {
      diamond: diamondBuffer,
      ruby: rubyBuffer
    };

    if (outputDir) {
      fs.writeFileSync(path.join(outputDir, `diamond_${name}.png`), diamondBuffer);
      fs.writeFileSync(path.join(outputDir, `ruby_${name}.png`), rubyBuffer);
    }
  }

  return results;
}

if (require.main === module) {
  (async () => {
    const args = process.argv.slice(2);
    let outputDirectory = path.join(process.cwd(), 'assets', 'textures', 'items');

    for (let i = 0; i < args.length; i++) {
      if (args[i] === '--output' && args[i + 1]) {
        outputDirectory = args[i + 1];
        i++;
      }
    }

    const generated = await generateRubyToolsets(outputDirectory);
    process.stdout.write(`Generated ${Object.keys(generated).length} Ruby toolset variants in ${outputDirectory}\n`);
  })();
}

exports.recolorToRuby = recolorToRuby;
exports.recolorPixel = recolorPixel;
exports.recolorRawBuffer = recolorRawBuffer;
exports.generateRubyToolsets = generateRubyToolsets;
exports.encodePNG = encodePNG;
exports.decodePNG = decodePNG;
exports.colorDistance = colorDistance;
exports.isDiamondMaterial = isDiamondMaterial;
exports.interpolateRubyRamp = interpolateRubyRamp;
exports.PALETTE_MAP = PALETTE_MAP;
exports.VANILLA_DIAMOND_TOOLS = VANILLA_DIAMOND_TOOLS;

module.exports = {
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
};
