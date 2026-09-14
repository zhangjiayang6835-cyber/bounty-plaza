import * as fs from 'fs';
import * as path from 'path';

/**
 * Resolves template fragments, scopes, and variable interpolation expressions.
 */
export class TemplateExpander {
  /**
   * Initializes the template expander with a template directory and default context.
   *
   * @param {string} templateDir - Directory containing reusable template fragments.
   * @param {Record<string, any>} defaultContext - Baseline variables for interpolation.
   */
  constructor(templateDir = 'templates', defaultContext = {}) {
    this.templateDir = templateDir;
    this.defaultContext = {
      namespace: 'tank',
      block_name: 'custom_block',
      texture: 'default_texture',
      sound: 'wood',
      geometry: 'geometry.custom_block',
      ...defaultContext,
    };
  }

  /**
   * Loads a template fragment from disk by identifier or filename.
   *
   * @param {string} templateName - Name or path of the template fragment.
   * @returns {string} Raw template string content.
   */
  loadFragment(templateName) {
    const cleanName = templateName.replace(/['"]/g, '').trim();
    const candidatePaths = [
      path.join(this.templateDir, cleanName.endsWith('.json') ? cleanName : `${cleanName}.json`),
      path.join(this.templateDir, cleanName),
      path.resolve(cleanName),
    ];

    for (const candidate of candidatePaths) {
      if (fs.existsSync(candidate)) {
        return fs.readFileSync(candidate, 'utf-8');
      }
    }

    throw new Error(`Template fragment not found: ${cleanName}`);
  }

  /**
   * Expands text containing template includes and variable interpolations.
   *
   * @param {string} rawText - Input template string.
   * @param {Record<string, any>} context - Scoped variables for expansion.
   * @returns {string} Fully expanded text.
   */
  expandString(rawText, context) {
    let result = rawText;

    const includePattern = /^[ \t]*\{\{(?:#template|>)\s+["']?([^"'}]+)["']?\}\}[ \t]*$/gm;
    result = result.replace(includePattern, (match, templateName) => {
      const fragment = this.loadFragment(templateName);
      let trimmed = fragment.trim();
      if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
        trimmed = trimmed.slice(1, -1).trim();
      }
      return trimmed;
    });

    const variablePattern = /\{\{\s*([\w:.-]+)\s*\}\}/g;
    result = result.replace(variablePattern, (match, key) => {
      if (key in context) {
        return String(context[key]);
      }
      return match;
    });

    const jinjaPattern = /\{%\s*set\s+(\w+)\s*=\s*["']?([^"']+)["']?\s*%\}/g;
    result = result.replace(jinjaPattern, (match, varName, varValue) => {
      context[varName] = varValue;
      return '';
    });

    return result;
  }

  /**
   * Recursively purges internal metadata properties such as $scope.
   *
   * @param {any} node - Current node in the parsed JSON tree.
   * @returns {any} Cleaned JSON tree node.
   */
  cleanMetadata(node) {
    if (Array.isArray(node)) {
      return node.map((item) => this.cleanMetadata(item));
    }
    if (node !== null && typeof node === 'object') {
      const output = {};
      for (const [key, value] of Object.entries(node)) {
        if (key.startsWith('$')) {
          continue;
        }
        output[key] = this.cleanMetadata(value);
      }
      return output;
    }
    return node;
  }

  /**
   * Determines if a file contains template directives or Jinja expressions.
   *
   * @param {string} content - Raw content of the file.
   * @returns {boolean} True if template directives are detected.
   */
  isTemplate(content) {
    return (
      content.includes('{{') ||
      content.includes('}}') ||
      content.includes('{%') ||
      content.includes('%}') ||
      content.includes('"$scope"')
    );
  }

  /**
   * Expands a template file or raw string into a standard JSON string.
   *
   * @param {string} content - File content.
   * @param {string} [filename] - Relative or absolute path for contextual hints.
   * @returns {string} Formatted standard JSON string.
   */
  expand(content, filename = '') {
    const fileContext = { ...this.defaultContext };

    if (filename) {
      const baseName = path.basename(filename, path.extname(filename));
      fileContext.block_name = baseName;
    }

    let preliminaryScope = {};
    try {
      const parsed = JSON.parse(content);
      if (parsed && typeof parsed === 'object' && parsed.$scope) {
        preliminaryScope = parsed.$scope;
      }
    } catch {
      const scopeMatch = content.match(/"\$scope"\s*:\s*\{([^}]+)\}/);
      if (scopeMatch) {
        try {
          preliminaryScope = JSON.parse(`{${scopeMatch[1]}}`);
        } catch {}
      }
    }

    const mergedContext = { ...fileContext, ...preliminaryScope };
    const expandedText = this.expandString(content, mergedContext);

    let parsedOutput;
    try {
      parsedOutput = JSON.parse(expandedText);
    } catch (err) {
      throw new Error(
        `Failed to parse expanded JSON for ${filename || 'input'}: ${err.message}\n` +
        `Expanded content:\n${expandedText}`
      );
    }

    const cleaned = this.cleanMetadata(parsedOutput);
    return JSON.stringify(cleaned, null, 2) + '\n';
  }
}
