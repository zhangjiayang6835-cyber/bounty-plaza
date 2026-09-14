import * as fs from 'fs';
import * as path from 'path';

/**
 * Calculates 1-indexed line and column numbers for a character offset in text.
 *
 * @param {string} text - Full source text.
 * @param {number} position - Zero-based index in text.
 * @returns {{ line: number, column: number }} Calculated line and column coordinates.
 */
function getLineAndColumn(text, position) {
  let line = 1;
  let column = 1;
  for (let i = 0; i < position && i < text.length; i++) {
    if (text[i] === '\n') {
      line++;
      column = 1;
    } else {
      column++;
    }
  }
  return { line, column };
}

/**
 * Extracts line and column coordinates from a V8 SyntaxError message or locates the character in text.
 *
 * @param {SyntaxError} error - Caught SyntaxError instance.
 * @param {string} content - Raw file content.
 * @returns {{ line: number, column: number, character: string }} Position details.
 */
function parseSyntaxErrorCoordinates(error, content) {
  const positionMatch = error.message.match(/at position (\d+)/);
  if (positionMatch) {
    const pos = parseInt(positionMatch[1], 10);
    const coords = getLineAndColumn(content, pos);
    const char = pos < content.length ? content[pos] : 'EOF';
    return { ...coords, character: char };
  }

  const lineColMatch = error.message.match(/line (\d+) column (\d+)/);
  if (lineColMatch) {
    const line = parseInt(lineColMatch[1], 10);
    const column = parseInt(lineColMatch[2], 10);
    const lines = content.split('\n');
    const targetLine = lines[line - 1] || '';
    const char = targetLine[column - 1] || '{';
    return { line, column, character: char };
  }

  for (let i = 0; i < content.length; i++) {
    if (content[i] === '{' && i > 0 && content[i - 1] === '{') {
      const coords = getLineAndColumn(content, i - 1);
      return { ...coords, character: '{' };
    }
  }

  return { line: 1, column: 1, character: 'unknown' };
}

/**
 * Validates Bedrock behavior pack JSON files for syntactic and structural correctness.
 */
export class PackValidator {
  /**
   * Scans a directory and validates all JSON files.
   *
   * @param {string} targetDir - Absolute or relative directory path to validate.
   * @returns {{ valid: boolean, fileCount: number, blockCount: number, errors: string[] }} Validation report.
   */
  static validatePack(targetDir) {
    if (!fs.existsSync(targetDir)) {
      throw new Error(`Directory does not exist: ${targetDir}`);
    }

    const errors = [];
    let fileCount = 0;
    let blockCount = 0;

    const files = this.collectJsonFiles(targetDir);

    for (const filePath of files) {
      fileCount++;
      const relativePath = path.relative(targetDir, filePath).replace(/\\/g, '/');
      const content = fs.readFileSync(filePath, 'utf-8');

      let parsed;
      try {
        parsed = JSON.parse(content);
      } catch (err) {
        const { line, column, character } = parseSyntaxErrorCoordinates(err, content);
        const formattedError =
          `[PackValidator][Error] Failed to parse JSON in '${relativePath}':\n` +
          `Syntax error: unexpected character '${character}' at line ${line} column ${column}`;
        errors.push(formattedError);
        continue;
      }

      const rawTemplateTokens = content.match(/(\{\{|\}\}|\{%|%\})/);
      if (rawTemplateTokens) {
        errors.push(
          `[PackValidator][Error] Unexpanded template token '${rawTemplateTokens[0]}' found in deployed file '${relativePath}'`
        );
        continue;
      }

      if (relativePath.startsWith('blocks/') || relativePath.includes('/blocks/')) {
        blockCount++;
        const blockError = this.validateBlockSchema(parsed, relativePath);
        if (blockError) {
          errors.push(blockError);
        }
      }
    }

    return {
      valid: errors.length === 0,
      fileCount,
      blockCount,
      errors,
    };
  }

  /**
   * Validates structure against canonical Bedrock block schemas.
   *
   * @param {Record<string, any>} json - Parsed JSON object.
   * @param {string} relativePath - Path for error reporting.
   * @returns {string | null} Error message if invalid, or null if valid.
   */
  static validateBlockSchema(json, relativePath) {
    if (!json.format_version) {
      return `[PackValidator][Error] Missing format_version in '${relativePath}'`;
    }
    const blockDef = json['minecraft:block'];
    if (!blockDef) {
      return `[PackValidator][Error] Missing 'minecraft:block' root object in '${relativePath}'`;
    }
    if (!blockDef.description || !blockDef.description.identifier) {
      return `[PackValidator][Error] Missing 'description.identifier' in '${relativePath}'`;
    }
    const id = blockDef.description.identifier;
    if (!id.includes(':')) {
      return `[PackValidator][Error] Block identifier '${id}' in '${relativePath}' must contain a namespace prefix`;
    }
    return null;
  }

  /**
   * Recursively discovers all JSON files within a folder.
   *
   * @param {string} dir - Directory to search.
   * @returns {string[]} List of full file paths.
   */
  static collectJsonFiles(dir) {
    const results = [];
    if (!fs.existsSync(dir)) {
      return results;
    }
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        results.push(...this.collectJsonFiles(fullPath));
      } else if (entry.isFile() && entry.name.endsWith('.json')) {
        results.push(fullPath);
      }
    }
    return results;
  }
}

if (process.argv[1] && process.argv[1].endsWith('pack_validator.js')) {
  const target = process.argv[2] || '_temp/behavior_pack';
  try {
    const report = PackValidator.validatePack(target);
    if (!report.valid) {
      console.error(report.errors.join('\n'));
      process.exit(1);
    }
    console.log(`[PackValidator] Successfully verified ${report.fileCount} JSON files (${report.blockCount} blocks).`);
  } catch (err) {
    console.error(`[PackValidator][Error] ${err.message}`);
    process.exit(1);
  }
}
