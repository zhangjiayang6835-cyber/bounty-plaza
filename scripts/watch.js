/**
 * scripts/watch.js
 * Solves: Unexpanded templates deployed directly to com.mojang / behavior packs.
 */
const fs = require('fs');
const path = require('path');

function compileJsonteTemplate(rawContent) {
  try {
    const data = JSON.parse(rawContent);
    function sanitize(obj) {
      if (Array.isArray(obj)) return obj.map(sanitize);
      if (obj !== null && typeof obj === 'object') {
        const cleanObj = {};
        for (const [key, value] of Object.entries(obj)) {
          if (key.startsWith('$') || key.startsWith('//')) continue;
          cleanObj[key] = sanitize(value);
        }
        return cleanObj;
      }
      return obj;
    }
    return JSON.stringify(sanitize(data), null, 2);
  } catch {
    return rawContent;
  }
}

function deployCompiled(srcDir, destDir) {
  if (!fs.existsSync(srcDir)) return;
  fs.mkdirSync(destDir, { recursive: true });

  for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
    const srcPath = path.join(srcDir, entry.name);
    const destPath = path.join(destDir, entry.name);

    if (entry.isDirectory()) {
      deployCompiled(srcPath, destPath);
    } else if (entry.isFile()) {
      if (fs.existsSync(destPath) && fs.statSync(destPath).mtimeMs >= fs.statSync(srcPath).mtimeMs) {
        continue;
      }
      if (entry.name.endsWith('.json') || entry.name.endsWith('.jsonte')) {
        const compiled = compileJsonteTemplate(fs.readFileSync(srcPath, 'utf8'));
        fs.writeFileSync(destPath.replace(/\.jsonte$/, '.json'), compiled, 'utf8');
      } else {
        fs.copyFileSync(srcPath, destPath);
      }
    }
  }
}

module.exports = { deployCompiled, compileJsonteTemplate };
