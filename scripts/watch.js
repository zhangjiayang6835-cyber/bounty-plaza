/**
 * Development watch and deployment script for Minecraft Bedrock behavior and resource packs.
 * Replaces direct unexpanded template copying with intermediate compilation filters.
 */

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

/**
 * Strip comments and trailing commas from JSON/JSONTE content.
 * @param {string} text - Raw JSON string potentially containing comments.
 * @returns {string} Clean JSON text.
 */
export function stripComments(text) {
  const result = [];
  let inString = false;
  let escape = false;
  let index = 0;
  const len = text.length;

  while (index < len) {
    const char = text[index];

    if (inString) {
      result.push(char);
      if (escape) {
        escape = false;
      } else if (char === '\\') {
        escape = true;
      } else if (char === '"') {
        inString = false;
      }
      index++;
      continue;
    }

    if (char === '"') {
      inString = true;
      result.push(char);
      index++;
      continue;
    }

    if (char === '/' && index + 1 < len) {
      const nextChar = text[index + 1];
      if (nextChar === '/') {
        index += 2;
        while (index < len && text[index] !== '\n' && text[index] !== '\r') {
          index++;
        }
        continue;
      }
      if (nextChar === '*') {
        index += 2;
        while (index < len && !(text[index] === '*' && text[index + 1] === '/')) {
          index++;
        }
        index += 2;
        continue;
      }
    }

    result.push(char);
    index++;
  }

  return result.join('').replace(/,\s*([\]}])/g, '$1');
}

/**
 * Deep merge source object into target object.
 * @param {any} target - Destination base object.
 * @param {any} source - Source object providing overrides.
 * @returns {any} Merged result.
 */
export function deepMerge(target, source) {
  if (target && typeof target === 'object' && !Array.isArray(target) &&
      source && typeof source === 'object' && !Array.isArray(source)) {
    const merged = { ...target };
    for (const key of Object.keys(source)) {
      if (key in merged && typeof merged[key] === 'object' && !Array.isArray(merged[key]) &&
          typeof source[key] === 'object' && !Array.isArray(source[key])) {
        merged[key] = deepMerge(merged[key], source[key]);
      } else {
        merged[key] = source[key];
      }
    }
    return merged;
  }
  return source;
}

/**
 * Resolve dotted variable path in evaluation context.
 * @param {string} expr - Expression path.
 * @param {Record<string, any>} context - Variable scope.
 * @returns {any}
 */
function lookupContext(expr, context) {
  const parts = expr.trim().split('.');
  let current = context;
  for (const part of parts) {
    if (current && typeof current === 'object' && part in current) {
      current = current[part];
    } else {
      return '';
    }
  }
  return current;
}

/**
 * Interpolate mustache expressions in string.
 * @param {string} text - Input text.
 * @param {Record<string, any>} context - Active scope.
 * @returns {any}
 */
function interpolateString(text, context) {
  const trimmed = text.trim();
  const exact = trimmed.match(/^\{\{([^{}]+)\}\}$/);
  if (exact) {
    const key = exact[1].trim();
    const val = lookupContext(key, context);
    if (val !== '' && val !== undefined) return val;
  }

  return text.replace(/\{\{([^{}]+)\}\}/g, (_, key) => {
    const val = lookupContext(key.trim(), context);
    return val !== undefined && val !== '' ? String(val) : '';
  });
}

/**
 * Expand JsonTE template AST node.
 * @param {any} node - Template node.
 * @param {Record<string, any>} context - Active scope.
 * @param {string} [baseDir] - Base directory for $extend references.
 * @param {Set<string>} [visited] - Set of visited template files.
 * @returns {any}
 */
export function expandTemplateNode(node, context, baseDir, visited = new Set()) {
  if (Array.isArray(node)) {
    const result = [];
    for (const item of node) {
      if (item && typeof item === 'object' && !Array.isArray(item)) {
        const keys = Object.keys(item);
        if (keys.length === 1 && keys[0].startsWith('{{#each') && keys[0].endsWith('}}')) {
          const iterExpr = keys[0].slice(7, -2).trim();
          let iterItems = null;
          if ((iterExpr.startsWith('[') && iterExpr.endsWith(']')) ||
              (iterExpr.startsWith('{') && iterExpr.endsWith('}'))) {
            try {
              iterItems = JSON.parse(iterExpr.replace(/'/g, '"'));
            } catch {
              iterItems = null;
            }
          }
          if (!iterItems) {
            iterItems = lookupContext(iterExpr, context);
          }
          if (Array.isArray(iterItems)) {
            for (let idx = 0; idx < iterItems.length; idx++) {
              const scope = { ...context, $index: idx, $value: iterItems[idx], this: iterItems[idx] };
              if (typeof iterItems[idx] === 'object') Object.assign(scope, iterItems[idx]);
              result.push(expandTemplateNode(item[keys[0]], scope, baseDir, visited));
            }
            continue;
          }
        }
      }
      result.push(expandTemplateNode(item, context, baseDir, visited));
    }
    return result;
  }

  if (node && typeof node === 'object') {
    let base = {};
    const extendTarget = node.$extend || node.$template;

    if (extendTarget) {
      const targets = Array.isArray(extendTarget) ? extendTarget : [extendTarget];
      for (const targetRef of targets) {
        const candidatePaths = [
          baseDir ? path.resolve(baseDir, targetRef) : null,
          baseDir ? path.resolve(baseDir, `${targetRef}.jsonte`) : null,
          baseDir ? path.resolve(baseDir, `${targetRef}.json`) : null,
          path.resolve(process.cwd(), targetRef),
          path.resolve(process.cwd(), `${targetRef}.jsonte`),
          path.resolve(process.cwd(), `${targetRef}.json`),
        ].filter(Boolean);

        let parentFile = candidatePaths.find(p => fs.existsSync(p) && fs.statSync(p).isFile());
        if (parentFile) {
          parentFile = path.resolve(parentFile);
          if (visited.has(parentFile)) {
            throw new Error(`Circular inheritance detected in ${parentFile}`);
          }
          const nextVisited = new Set(visited);
          nextVisited.add(parentFile);

          const rawParent = fs.readFileSync(parentFile, 'utf8');
          const parsedParent = JSON.parse(stripComments(rawParent));
          const expandedParent = expandTemplateNode(parsedParent, context, path.dirname(parentFile), nextVisited);
          base = deepMerge(base, expandedParent);
        }
      }
    }

    const current = {};
    const localContext = { ...context };
    if (node.$scope && typeof node.$scope === 'object') Object.assign(localContext, node.$scope);
    if (node.$variables && typeof node.$variables === 'object') Object.assign(localContext, node.$variables);

    for (const [key, val] of Object.entries(node)) {
      if (key === '$extend' || key === '$template' || key === '$scope' || key === '$variables') {
        continue;
      }

      if (key.startsWith('{{#if') && key.endsWith('}}')) {
        const condExpr = key.slice(5, -2).trim();
        const truthy = Boolean(lookupContext(condExpr, localContext));
        if (truthy && val && typeof val === 'object' && !Array.isArray(val)) {
          const subExpanded = expandTemplateNode(val, localContext, baseDir, visited);
          Object.assign(current, subExpanded);
        }
        continue;
      }

      if (key.startsWith('{{#each') && key.endsWith('}}')) {
        const iterExpr = key.slice(7, -2).trim();
        let iterItems = null;
        if ((iterExpr.startsWith('[') && iterExpr.endsWith(']')) ||
            (iterExpr.startsWith('{') && iterExpr.endsWith('}'))) {
          try {
            iterItems = JSON.parse(iterExpr.replace(/'/g, '"'));
          } catch {
            iterItems = null;
          }
        }
        if (!iterItems) {
          iterItems = lookupContext(iterExpr, localContext);
        }
        if (Array.isArray(iterItems)) {
          for (let idx = 0; idx < iterItems.length; idx++) {
            const scope = { ...localContext, $index: idx, $value: iterItems[idx], this: iterItems[idx] };
            if (typeof iterItems[idx] === 'object') Object.assign(scope, iterItems[idx]);
            const expandedSub = expandTemplateNode(val, scope, baseDir, visited);
            if (expandedSub && typeof expandedSub === 'object') {
              Object.assign(current, expandedSub);
            }
          }
        }
        continue;
      }

      const resolvedKey = String(interpolateString(key, localContext));
      current[resolvedKey] = expandTemplateNode(val, localContext, baseDir, visited);
    }

    return deepMerge(base, current);
  }

  if (typeof node === 'string') {
    return interpolateString(node, context);
  }

  return node;
}

/**
 * Clean all template directives and emit valid Bedrock JSON.
 * @param {any} node - Output data structure.
 * @returns {any} Sanitized node.
 */
export function sanitizeBedrockJson(node) {
  if (Array.isArray(node)) {
    return node.map(sanitizeBedrockJson);
  }
  if (node && typeof node === 'object') {
    const clean = {};
    for (const [k, v] of Object.entries(node)) {
      if (k.startsWith('$') || k.startsWith('//')) continue;
      clean[k] = sanitizeBedrockJson(v);
    }
    return clean;
  }
  if (typeof node === 'string') {
    return node.replace(/\{\{[^{}]*\}\}/g, '');
  }
  return node;
}

/**
 * Compile raw JsonTE string to strictly formatted Bedrock JSON.
 * @param {string} rawContent - Raw JSONTE file content.
 * @param {Record<string, any>} [context] - Evaluation context.
 * @param {string} [baseDir] - Base directory for imports.
 * @returns {string} Formatted JSON string.
 */
export function compileJsonte(rawContent, context = {}, baseDir = process.cwd()) {
  const clean = stripComments(rawContent);
  const parsed = JSON.parse(clean);
  const expanded = expandTemplateNode(parsed, context, baseDir);
  const sanitized = sanitizeBedrockJson(expanded);
  return JSON.stringify(sanitized, null, 2);
}

/**
 * Compile audio sound definitions for Bedrock resource packs.
 * @param {string} soundsDir - Directory containing audio assets.
 * @param {string} [existingDefsPath] - Optional path to existing definitions.
 * @returns {object} Valid sound_definitions.json object.
 */
export function compileSoundDefinitions(soundsDir, existingDefsPath) {
  const result = {
    format_version: '1.20.0',
    sound_definitions: {},
  };

  if (existingDefsPath && fs.existsSync(existingDefsPath)) {
    try {
      const loaded = JSON.parse(fs.readFileSync(existingDefsPath, 'utf8'));
      if (loaded.sound_definitions) {
        result.sound_definitions = { ...loaded.sound_definitions };
      }
    } catch {
      // Keep base
    }
  }

  if (!fs.existsSync(soundsDir) || !fs.statSync(soundsDir).isDirectory()) {
    return result;
  }

  function walk(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(full);
      } else if (entry.isFile() && /\.(ogg|wav|fsb)$/i.test(entry.name)) {
        const rel = path.relative(soundsDir, full).replace(/\\/g, '/');
        const ref = 'sounds/' + rel.replace(/\.[^.]+$/, '');
        const eventKey = rel.replace(/\.[^.]+$/, '').replace(/[\/\\]/g, '.');
        const cleanKey = eventKey.replace(/\d+$/, '');

        if (!result.sound_definitions[cleanKey]) {
          result.sound_definitions[cleanKey] = {
            category: 'player',
            sounds: [],
          };
        }
        if (!result.sound_definitions[cleanKey].sounds.includes(ref)) {
          result.sound_definitions[cleanKey].sounds.push(ref);
        }
      }
    }
  }

  walk(soundsDir);
  return result;
}

/**
 * Compute SHA-256 hash of file.
 * @param {string} filepath - Path to target file.
 * @returns {string} Hex hash digest.
 */
function fileHash(filepath) {
  const data = fs.readFileSync(filepath);
  return crypto.createHash('sha256').update(data).digest('hex');
}

/**
 * Deploy source directory to destination using the compiled filter pipeline.
 * Solves Issue #1207: Intermediate filters execute before files reach destination.
 * @param {string} srcDir - Source data directory (e.g. source/resources/data).
 * @param {string} destDir - Destination game folder in com.mojang.
 * @param {object} [options] - Build pipeline options.
 * @returns {{ filesProcessed: number, templatesCompiled: number, cached: number }}
 */
export function deployDirect(srcDir, destDir, options = {}) {
  if (!fs.existsSync(srcDir)) {
    return { filesProcessed: 0, templatesCompiled: 0, cached: 0 };
  }

  fs.mkdirSync(destDir, { recursive: true });
  const cacheFile = options.cacheFile || path.join(destDir, '.build_cache.json');
  let cache = {};
  if (fs.existsSync(cacheFile)) {
    try {
      cache = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
    } catch {
      cache = {};
    }
  }

  let filesProcessed = 0;
  let templatesCompiled = 0;
  let cachedCount = 0;

  function processDirectory(currentSrc, currentDest) {
    fs.mkdirSync(currentDest, { recursive: true });
    const entries = fs.readdirSync(currentSrc, { withFileTypes: true });

    for (const entry of entries) {
      const srcPath = path.join(currentSrc, entry.name);
      const destPath = path.join(currentDest, entry.name);

      if (entry.isDirectory()) {
        processDirectory(srcPath, destPath);
      } else if (entry.isFile()) {
        filesProcessed++;
        const currentHash = fileHash(srcPath);
        const rel = path.relative(srcDir, srcPath);

        const isJsonte = entry.name.endsWith('.jsonte');
        const isJson = entry.name.endsWith('.json');
        const targetDest = isJsonte ? destPath.replace(/\.jsonte$/, '.json') : destPath;

        if (!options.force && cache[rel] === currentHash && fs.existsSync(targetDest)) {
          cachedCount++;
          continue;
        }

        if (isJsonte || isJson) {
          const content = fs.readFileSync(srcPath, 'utf8');
          const isTemplate = isJsonte || content.includes('$extend') || content.includes('$template') ||
                             content.includes('{{#') || content.includes('{{');

          if (isTemplate) {
            const compiled = compileJsonte(content, options.context || {}, path.dirname(srcPath));
            fs.writeFileSync(targetDest, compiled, 'utf8');
            templatesCompiled++;
          } else {
            fs.copyFileSync(srcPath, targetDest);
          }
        } else {
          fs.copyFileSync(srcPath, targetDest);
        }

        cache[rel] = currentHash;
      }
    }
  }

  processDirectory(srcDir, destDir);

  const soundsDir = path.join(srcDir, 'sounds');
  if (fs.existsSync(soundsDir) && fs.statSync(soundsDir).isDirectory()) {
    const soundDefs = compileSoundDefinitions(soundsDir);
    const soundDest = path.join(destDir, 'sounds', 'sound_definitions.json');
    fs.mkdirSync(path.dirname(soundDest), { recursive: true });
    fs.writeFileSync(soundDest, JSON.stringify(soundDefs, null, 2), 'utf8');
  }

  try {
    fs.writeFileSync(cacheFile, JSON.stringify(cache, null, 2), 'utf8');
  } catch {
    // Non-critical cache write
  }

  return {
    filesProcessed,
    templatesCompiled,
    cached: cachedCount,
  };
}

/**
 * Continuous watch mode compilation daemon.
 * @param {string} srcDir - Source directory.
 * @param {string} destDir - Destination directory.
 * @param {object} [options] - Options.
 * @returns {fs.FSWatcher}
 */
export function watchAndDeploy(srcDir, destDir, options = {}) {
  deployDirect(srcDir, destDir, options);
  let debounceTimeout = null;

  return fs.watch(srcDir, { recursive: true }, (eventType, filename) => {
    if (debounceTimeout) clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      deployDirect(srcDir, destDir, options);
    }, 50);
  });
}
