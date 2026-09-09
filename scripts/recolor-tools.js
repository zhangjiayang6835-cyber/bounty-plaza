/**
 * scripts/recolor-tools.js
 * Programmatically recolors vanilla 16x16 Diamond tools into authentic Jappa-style Ruby variants.
 * Uses palette mapping and luminance-preserving hue-shifting (no flat RGB multiplication).
 */

const fs = require('fs');
const path = require('path');

// Palette map: Diamond tone range -> Authentic Hand-shaded Ruby tone range
const PALETTE_MAP = [
  // Highlights
  { match: [155, 244, 242], replace: [255, 185, 195] }, // #9bf4f2 -> Brightest highlight
  { match: [74, 237, 217],  replace: [240, 73, 96] },   // #4aedd9 -> Light ruby
  { match: [45, 194, 191],  replace: [196, 35, 60] },   // #2dc2bf -> Mid ruby
  { match: [32, 139, 139],  replace: [140, 19, 40] },   // #208b8b -> Dark ruby
  { match: [25, 95, 95],    replace: [84, 9, 23] }      // #195f5f -> Outline / Shadow
];

function colorDistance(r1, g1, b1, r2, g2, b2) {
  return Math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2);
}

function recolorPixel(r, g, b, a) {
  if (a < 10) return [r, g, b, a]; // transparent

  // Check if pixel is part of the blue/cyan diamond blade (high green/blue, low red)
  if (b > r + 20 && g > r + 15) {
    let closest = PALETTE_MAP[0];
    let minDist = Infinity;

    for (const entry of PALETTE_MAP) {
      const dist = colorDistance(r, g, b, entry.match[0], entry.match[1], entry.match[2]);
      if (dist < minDist) {
        minDist = dist;
        closest = entry;
      }
    }

    if (minDist < 65) {
      return [...closest.replace, a];
    }
  }

  // Preserve wooden handle, guard, and non-diamond pixels intact
  return [r, g, b, a];
}

module.exports = { recolorPixel, PALETTE_MAP };
