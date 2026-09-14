import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateCompressedBasaltDefinition } from './blocks/index.js';

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(currentDir, '..');
const blockPath = path.join(rootDir, 'blocks', 'compressed_basalt.json');

/**
 * Initializes and validates custom block definitions upon runtime startup.
 * @returns {number} Exit code: 0 on successful validation, 1 on failure.
 */
export function main() {
  if (!fs.existsSync(blockPath)) {
    process.stderr.write(`Block definition not found: ${blockPath}\n`);
    return 1;
  }

  const raw = fs.readFileSync(blockPath, 'utf-8');
  const doc = JSON.parse(raw);
  const result = validateCompressedBasaltDefinition(doc);

  if (!result.valid) {
    process.stderr.write(`Validation failed for 'custom:compressed_basalt':\n`);
    for (const error of result.errors) {
      process.stderr.write(` - ${error}\n`);
    }
    return 1;
  }

  process.stdout.write(`Custom block 'custom:compressed_basalt' validated successfully.\n`);
  return 0;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  process.exit(main());
}
