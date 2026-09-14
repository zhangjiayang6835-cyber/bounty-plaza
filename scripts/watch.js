// scripts/watch.js
const fs = require('fs');
const path = require('path');

function compileJsonte(rawText) {
  try {
    const parsed = JSON.parse(rawText);
    function sanitize(item) {
      if (Array.isArray(item)) return item.map(sanitize);
      if (item !== null && typeof item === 'object') {
        const out = {};
        for (const [k, v] of Object.entries(item)) {
          if (k.startsWith('$') || k.startsWith('//')) continue;
          out[k] = sanitize(v);
        }
        return out;
      }
      return item;
    }
    return JSON.stringify(sanitize(parsed), null, 2);
  } catch {
    return rawText.replace(/\$extend.*?;/g, '').replace(/\{\{.*?\}\}/g, '');
  }
}

export function deployDirect(srcDir, destDir) {
  if (!fs.existsSync(srcDir)) return;
  fs.mkdirSync(destDir, { recursive: true });

  for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
    const src = path.join(srcDir, entry.name);
    const dest = path.join(destDir, entry.name);

    if (entry.isDirectory()) {
      deployDirect(src, dest);
    } else if (entry.isFile()) {
      if (entry.name.endsWith('.json') || entry.name.endsWith('.jsonte')) {
        const compiled = compileJsonte(fs.readFileSync(src, 'utf-8'));
        const targetPath = dest.replace(/\.jsonte$/, '.json');
        fs.writeFileSync(targetPath, compiled, 'utf-8');
      } else {
        fs.copyFileSync(src, dest);
      }
    }
  }
}

module.exports = { deployDirect, compileJsonte };
