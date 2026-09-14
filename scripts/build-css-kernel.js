/**
 * @fileoverview Zero-allocation CSS kernel compiler and layout verification engine.
 */

const fs = require('node:fs');
const path = require('node:path');
const { performance } = require('node:perf_hooks');

/**
 * Minifies raw CSS text by stripping redundant whitespace and semicolons.
 * @param {string} css
 * @returns {string}
 */
function minifyCss(css) {
  return css
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\s+/g, ' ')
    .replace(/\s*([{}:;,])\s*/g, '$1')
    .replace(/;}/g, '}')
    .trim();
}

/**
 * Parses simple CSS rules into a structured representation.
 * @param {string} css
 * @returns {Array<{selector: string, declarations: Record<string, string>}>}
 */
function parseCssRules(css) {
  const stripped = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const ruleRegex = /([^{]+)\{([^}]+)\}/g;
  const rules = [];
  let match;

  while ((match = ruleRegex.exec(stripped)) !== null) {
    const selector = match[1].trim();
    const body = match[2].trim();
    const declarations = {};

    const declPairs = body.split(';');
    for (const pair of declPairs) {
      const trimmedPair = pair.trim();
      if (!trimmedPair) {
        continue;
      }
      const colonIdx = trimmedPair.indexOf(':');
      if (colonIdx === -1) {
        continue;
      }
      const prop = trimmedPair.slice(0, colonIdx).trim().toLowerCase();
      const val = trimmedPair.slice(colonIdx + 1).trim();
      declarations[prop] = val;
    }

    rules.push({ selector, declarations });
  }

  return rules;
}

/**
 * Validates layout centering and zero-allocation properties for target selectors.
 * @param {Array<{selector: string, declarations: Record<string, string>}>} rules
 */
function validateKernelLayout(rules) {
  const centerRule = rules.find((r) => r.selector.split(',').map((s) => s.trim()).includes('.center-everything'));

  if (!centerRule) {
    throw new Error("Validation failure: '.center-everything' selector is missing in styles/core.css");
  }

  const decls = centerRule.declarations;
  const hasGridCentering = decls['display'] === 'grid' &&
    (decls['place-items'] === 'center' || (decls['justify-items'] === 'center' && decls['align-items'] === 'center'));
  const hasFlexCentering = decls['display'] === 'flex' &&
    decls['justify-content'] === 'center' && decls['align-items'] === 'center';
  const hasPlaceContent = decls['place-content'] === 'center';

  if (!hasGridCentering && !hasFlexCentering && !hasPlaceContent) {
    throw new Error("Validation failure: '.center-everything' does not specify valid horizontal and vertical centering rules");
  }

  const hasContainment = decls['contain'] && decls['contain'].includes('layout');
  const hasWillChange = Boolean(decls['will-change']);

  if (!hasContainment && !hasWillChange) {
    process.stdout.write("Notice: Recommend adding 'contain: layout paint' or 'will-change: transform' to eliminate layout thrashing.\n");
  }

  return {
    hasGridCentering,
    hasFlexCentering,
    hasContainment: Boolean(hasContainment),
    hasWillChange
  };
}

/**
 * Main build execution pipeline for CSS kernel.
 */
function buildCssKernel() {
  const startTime = performance.now();
  const rootDir = path.resolve(__dirname, '..');
  const sourcePath = path.join(rootDir, 'styles', 'core.css');
  const distDir = path.join(rootDir, 'dist');
  const distPath = path.join(distDir, 'core.css');
  const distMinPath = path.join(distDir, 'core.min.css');

  if (!fs.existsSync(sourcePath)) {
    throw new Error(`Source file not found at ${sourcePath}`);
  }

  const sourceCss = fs.readFileSync(sourcePath, 'utf8');
  const parsedRules = parseCssRules(sourceCss);
  const validationResult = validateKernelLayout(parsedRules);

  if (!fs.existsSync(distDir)) {
    fs.mkdirSync(distDir, { recursive: true });
  }

  const minifiedCss = minifyCss(sourceCss);

  fs.writeFileSync(distPath, sourceCss, 'utf8');
  fs.writeFileSync(distMinPath, minifiedCss, 'utf8');

  const durationMs = performance.now() - startTime;

  process.stdout.write('========================================\n');
  process.stdout.write('CSS Kernel Compilation Report\n');
  process.stdout.write('========================================\n');
  process.stdout.write(`Source File:       ${sourcePath}\n`);
  process.stdout.write(`Rules Processed:   ${parsedRules.length}\n`);
  process.stdout.write(`Artifact (full):   ${distPath} (${Buffer.byteLength(sourceCss)} bytes)\n`);
  process.stdout.write(`Artifact (min):    ${distMinPath} (${Buffer.byteLength(minifiedCss)} bytes)\n`);
  process.stdout.write(`Grid Centering:    ${validationResult.hasGridCentering}\n`);
  process.stdout.write(`Layout Isolation:  ${validationResult.hasContainment}\n`);
  process.stdout.write(`Compilation Time:  ${durationMs.toFixed(2)}ms\n`);
  process.stdout.write('Status:            BUILD SUCCESS\n');
  process.stdout.write('========================================\n');
}

if (require.main === module) {
  try {
    buildCssKernel();
  } catch (error) {
    process.stderr.write(`Build Error: ${error.message}\n`);
    process.exit(1);
  }
}

module.exports = {
  minifyCss,
  parseCssRules,
  validateKernelLayout,
  buildCssKernel
};
