#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';

const TOOLS = ['sword', 'pickaxe', 'axe', 'shovel', 'hoe'];

function parseArgs(argv) {
  const out = {
    inputDir: path.resolve('textures/items'),
    outputDir: path.resolve('textures/items'),
    targetHue: 352,
    items: TOOLS,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    const next = argv[i + 1];
    if (arg === '--input-dir' && next) { out.inputDir = path.resolve(next); i += 1; }
    else if (arg === '--output-dir' && next) { out.outputDir = path.resolve(next); i += 1; }
    else if (arg === '--target-hue' && next) { out.targetHue = Number(next); i += 1; }
    else if (arg === '--items' && next) { out.items = next.split(',').map((v) => v.trim()).filter(Boolean); i += 1; }
    else if (arg === '--help' || arg === '-h') {
      console.log(`Usage: node generate-ruby-toolset.mjs [options]\n\nOptions:\n  --input-dir DIR    Directory containing diamond_<tool>.png files\n  --output-dir DIR   Destination for ruby_<tool>.png files (default: textures/items)\n  --items LIST       Comma-separated subset of sword,pickaxe,axe,shovel,hoe\n  --target-hue DEG   Ruby target hue in degrees (default: 352)\n`);
      process.exit(0);
    } else {
      throw new Error(`Unknown or incomplete argument: ${arg}`);
    }
  }
  if (!Number.isFinite(out.targetHue)) throw new Error('--target-hue must be a number');
  for (const item of out.items) {
    if (!TOOLS.includes(item)) throw new Error(`Unsupported tool: ${item}`);
  }
  return out;
}

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
  const typeBuf = Buffer.from(type, 'ascii');
  const length = Buffer.alloc(4); length.writeUInt32BE(data.length, 0);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])), 0);
  return Buffer.concat([length, typeBuf, data, crc]);
}

function paeth(a, b, c) {
  const p = a + b - c;
  const pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
  if (pa <= pb && pa <= pc) return a;
  return pb <= pc ? b : c;
}

function unfilter(raw, width, height, bpp) {
  const stride = width * bpp;
  const out = Buffer.alloc(height * stride);
  let src = 0;
  for (let y = 0; y < height; y += 1) {
    const filter = raw[src++];
    const rowStart = y * stride;
    for (let x = 0; x < stride; x += 1) {
      const val = raw[src++];
      const left = x >= bpp ? out[rowStart + x - bpp] : 0;
      const up = y > 0 ? out[rowStart - stride + x] : 0;
      const upLeft = y > 0 && x >= bpp ? out[rowStart - stride + x - bpp] : 0;
      let decoded;
      if (filter === 0) decoded = val;
      else if (filter === 1) decoded = (val + left) & 0xff;
      else if (filter === 2) decoded = (val + up) & 0xff;
      else if (filter === 3) decoded = (val + Math.floor((left + up) / 2)) & 0xff;
      else if (filter === 4) decoded = (val + paeth(left, up, upLeft)) & 0xff;
      else throw new Error(`Unsupported PNG filter: ${filter}`);
      out[rowStart + x] = decoded;
    }
  }
  return out;
}

export function decodePng(file) {
  const buf = fs.readFileSync(file);
  const sig = Buffer.from([137,80,78,71,13,10,26,10]);
  if (!buf.subarray(0,8).equals(sig)) throw new Error(`${file}: not a PNG`);
  let pos = 8, width, height, bitDepth, colorType, interlace, palette = null, trns = null;
  const idat = [];
  while (pos < buf.length) {
    const len = buf.readUInt32BE(pos); pos += 4;
    const type = buf.toString('ascii', pos, pos + 4); pos += 4;
    const data = buf.subarray(pos, pos + len); pos += len + 4; // skip CRC after data
    if (type === 'IHDR') {
      width = data.readUInt32BE(0); height = data.readUInt32BE(4);
      bitDepth = data[8]; colorType = data[9]; interlace = data[12];
    } else if (type === 'PLTE') palette = Buffer.from(data);
    else if (type === 'tRNS') trns = Buffer.from(data);
    else if (type === 'IDAT') idat.push(data);
    else if (type === 'IEND') break;
  }
  if (bitDepth !== 8) throw new Error(`${file}: only 8-bit PNGs are supported`);
  if (interlace !== 0) throw new Error(`${file}: interlaced PNGs are not supported`);
  const channelsByType = {0:1,2:3,3:1,4:2,6:4};
  const bpp = channelsByType[colorType];
  if (!bpp) throw new Error(`${file}: unsupported color type ${colorType}`);
  const raw = zlib.inflateSync(Buffer.concat(idat));
  const pixels = unfilter(raw, width, height, bpp);
  const rgba = Buffer.alloc(width * height * 4);
  for (let i = 0, j = 0; i < pixels.length; i += bpp, j += 4) {
    if (colorType === 6) { rgba[j]=pixels[i]; rgba[j+1]=pixels[i+1]; rgba[j+2]=pixels[i+2]; rgba[j+3]=pixels[i+3]; }
    else if (colorType === 2) { rgba[j]=pixels[i]; rgba[j+1]=pixels[i+1]; rgba[j+2]=pixels[i+2]; rgba[j+3]=255; }
    else if (colorType === 0) { rgba[j]=rgba[j+1]=rgba[j+2]=pixels[i]; rgba[j+3]=255; }
    else if (colorType === 4) { rgba[j]=rgba[j+1]=rgba[j+2]=pixels[i]; rgba[j+3]=pixels[i+1]; }
    else {
      const idx = pixels[i];
      if (!palette || idx * 3 + 2 >= palette.length) throw new Error(`${file}: invalid indexed PNG palette`);
      rgba[j]=palette[idx*3]; rgba[j+1]=palette[idx*3+1]; rgba[j+2]=palette[idx*3+2]; rgba[j+3]=trns && idx < trns.length ? trns[idx] : 255;
    }
  }
  return { width, height, rgba };
}

export function encodePng(width, height, rgba) {
  const signature = Buffer.from([137,80,78,71,13,10,26,10]);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0); ihdr.writeUInt32BE(height, 4);
  ihdr[8]=8; ihdr[9]=6; ihdr[10]=0; ihdr[11]=0; ihdr[12]=0;
  const stride = width * 4;
  const raw = Buffer.alloc(height * (stride + 1));
  for (let y = 0; y < height; y += 1) {
    const dst = y * (stride + 1); raw[dst] = 0;
    rgba.copy(raw, dst + 1, y * stride, (y + 1) * stride);
  }
  const compressed = zlib.deflateSync(raw, { level: 9, strategy: zlib.constants.Z_FIXED });
  return Buffer.concat([signature, pngChunk('IHDR', ihdr), pngChunk('IDAT', compressed), pngChunk('IEND', Buffer.alloc(0))]);
}

function rgbToHsv(r, g, b) {
  const rf=r/255, gf=g/255, bf=b/255;
  const max=Math.max(rf,gf,bf), min=Math.min(rf,gf,bf), d=max-min;
  let h=0;
  if (d !== 0) {
    if (max === rf) h = 60 * (((gf - bf) / d) % 6);
    else if (max === gf) h = 60 * (((bf - rf) / d) + 2);
    else h = 60 * (((rf - gf) / d) + 4);
  }
  if (h < 0) h += 360;
  return [h, max === 0 ? 0 : d / max, max];
}

function hsvToRgb(h, s, v) {
  h = ((h % 360) + 360) % 360;
  const c = v*s, x = c*(1-Math.abs(((h/60)%2)-1)), m=v-c;
  let rp=0,gp=0,bp=0;
  if (h < 60) [rp,gp,bp]=[c,x,0];
  else if (h < 120) [rp,gp,bp]=[x,c,0];
  else if (h < 180) [rp,gp,bp]=[0,c,x];
  else if (h < 240) [rp,gp,bp]=[0,x,c];
  else if (h < 300) [rp,gp,bp]=[x,0,c];
  else [rp,gp,bp]=[c,0,x];
  return [Math.round((rp+m)*255), Math.round((gp+m)*255), Math.round((bp+m)*255)];
}

function isDiamondBlue(h, s, v, a) {
  return a > 0 && s >= 0.20 && v >= 0.12 && h >= 155 && h <= 220;
}

export function recolorToRuby(rgba, targetHue) {
  const candidates = [];
  for (let i=0; i<rgba.length; i+=4) {
    const a=rgba[i+3];
    if (a === 0) { rgba[i]=0; rgba[i+1]=0; rgba[i+2]=0; continue; }
    const hsv=rgbToHsv(rgba[i],rgba[i+1],rgba[i+2]);
    if (isDiamondBlue(hsv[0],hsv[1],hsv[2],a)) candidates.push({i,h:hsv[0],s:hsv[1],v:hsv[2]});
  }
  if (candidates.length === 0) throw new Error('No diamond-blue pixels detected');
  let sumSin=0, sumCos=0;
  for (const p of candidates) {
    const rad=p.h*Math.PI/180; const w=Math.max(0.001,p.s*p.v);
    sumSin += Math.sin(rad)*w; sumCos += Math.cos(rad)*w;
  }
  let center=Math.atan2(sumSin,sumCos)*180/Math.PI; if(center<0) center+=360;
  const delta=targetHue-center;
  for (const p of candidates) {
    const [r,g,b]=hsvToRgb(p.h+delta,p.s,p.v);
    rgba[p.i]=r; rgba[p.i+1]=g; rgba[p.i+2]=b;
  }
  return { recolored: candidates.length, sourceHueCenter: center };
}

export function processTexture(inputPath, outputPath, targetHue) {
  const {width,height,rgba}=decodePng(inputPath);
  if (width !== 16 || height !== 16) throw new Error(`${inputPath}: expected 16x16 PNG, got ${width}x${height}`);
  const result=recolorToRuby(rgba,targetHue);
  fs.mkdirSync(path.dirname(outputPath), {recursive:true});
  fs.writeFileSync(outputPath, encodePng(width,height,rgba));
  return result;
}

function main() {
  const opts=parseArgs(process.argv.slice(2));
  for (const item of opts.items) {
    const input=path.join(opts.inputDir, `diamond_${item}.png`);
    const output=path.join(opts.outputDir, `ruby_${item}.png`);
    if (!fs.existsSync(input)) throw new Error(`Missing input texture: ${input}`);
    const {recolored,sourceHueCenter}=processTexture(input,output,opts.targetHue);
    console.log(`${item}: ${recolored} pixels recolored (source hue ${sourceHueCenter.toFixed(1)}°) -> ${output}`);
  }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  try { main(); } catch (err) { console.error(`error: ${err.message}`); process.exitCode=1; }
}
