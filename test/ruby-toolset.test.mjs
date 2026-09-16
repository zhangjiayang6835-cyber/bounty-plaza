import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {
  decodePng,
  encodePng,
  processTexture,
  recolorToRuby
} from '../scripts/tools/generate-ruby-toolset.mjs';

function fixturePixels() {
  const rgba = Buffer.alloc(16 * 16 * 4);
  for (let i = 0; i < rgba.length; i += 4) {
    rgba[i] = 77; rgba[i + 1] = 22; rgba[i + 2] = 11; rgba[i + 3] = 0;
  }
  const set = (x,y,c) => { const i=(y*16+x)*4; rgba.set(c,i); };
  const blues = [[25,90,95,255],[32,160,165,255],[60,210,205,255],[120,245,235,255]];
  for (let y=2; y<7; y+=1) for (let x=3; x<10; x+=1) set(x,y,blues[(x+y)%blues.length]);
  for (let k=0; k<6; k+=1) set(7+k,8+k,[110,70,35,255]);
  set(2,2,[50,50,50,255]);
  return rgba;
}

const pixel = (rgba,x,y) => [...rgba.subarray((y*16+x)*4,(y*16+x)*4+4)];

test('recolors blue pixels while preserving handle, neutrals, value and alpha', () => {
  const rgba = fixturePixels();
  const before = Buffer.from(rgba);
  const result = recolorToRuby(rgba, 352);
  assert.ok(result.recolored > 0);
  assert.deepEqual(pixel(rgba,8,9), pixel(before,8,9));
  assert.deepEqual(pixel(rgba,2,2), pixel(before,2,2));
  assert.notDeepEqual(pixel(rgba,3,3), pixel(before,3,3));
  assert.equal(pixel(rgba,3,3)[3], 255);
});

test('normalizes fully transparent pixels to transparent black', () => {
  const rgba = fixturePixels();
  recolorToRuby(rgba, 352);
  assert.deepEqual(pixel(rgba,0,0), [0,0,0,0]);
});

test('writes deterministic 16x16 RGBA PNG output', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(),'ruby-toolset-'));
  const input = path.join(dir,'diamond_sword.png');
  const a = path.join(dir,'a.png');
  const b = path.join(dir,'b.png');
  fs.writeFileSync(input, encodePng(16,16,fixturePixels()));
  processTexture(input,a,352);
  processTexture(input,b,352);
  const hash = (p) => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
  assert.equal(hash(a),hash(b));
  const decoded=decodePng(a);
  assert.equal(decoded.width,16); assert.equal(decoded.height,16);
});

test('rejects non-16x16 textures', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(),'ruby-toolset-'));
  const input = path.join(dir,'bad.png');
  fs.writeFileSync(input, encodePng(8,8,Buffer.alloc(8*8*4,255)));
  assert.throws(() => processTexture(input,path.join(dir,'out.png'),352), /expected 16x16/);
});
