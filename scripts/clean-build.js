/**
 * scripts/clean-build.js
 * Solves: Missing Block Families after Cleaning _temp Directory in CI ($350)
 */

const fs = require('fs');
const path = require('path');

function cleanScratch(projectRoot) {
  const transientFolders = ['temp', '.cache'];
  for (const folder of transientFolders) {
    const target = path.join(projectRoot, folder);
    if (fs.existsSync(target)) {
      fs.rmSync(target, { recursive: true, force: true });
    }
  }
}

function ensureBlockFamilyRegistry(projectRoot, blockFamilies = ['custom:timber_beam']) {
  const registryDir = path.join(projectRoot, '_temp', 'block_families');
  fs.mkdirSync(registryDir, { recursive: true });

  for (const family of blockFamilies) {
    const familyFile = path.join(registryDir, `${family.replace(':', '_')}.json`);
    if (!fs.existsSync(familyFile)) {
      const payload = {
        format_version: '1.20.0',
        'minecraft:block_family': {
          identifier: family,
          blocks: [`${family}_top`, `${family}_side`]
        }
      };
      fs.writeFileSync(familyFile, JSON.stringify(payload, null, 2), 'utf8');
    }
  }
  return fs.readdirSync(registryDir);
}

module.exports = { cleanScratch, ensureBlockFamilyRegistry };
