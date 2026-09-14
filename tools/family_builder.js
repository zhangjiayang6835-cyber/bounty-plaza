import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import { TemplateExpander } from './template_expander.js';
/**
 * Options for generating block family metadata catalogs.
 *
 * @typedef {object} FamilyBuilderOptions
 * @property {string} [stagingDir='_temp/behavior_pack'] - Directory containing staged pack assets.
 * @property {string} [stagingBase='_temp'] - Base temporary staging directory.
 * @property {string} [sourceDir='packs/behavior_pack'] - Directory containing source pack assets.
 * @property {string} [templateDir='templates'] - Directory containing template fragments.
 * @property {string} [catalogPath] - Explicit file path for catalog output.
 * @property {boolean} [requireExisting=false] - Enforces pre-existing catalog requirement.
 */
/**
 * Block family entry metadata.
 *
 * @typedef {object} FamilyEntry
 * @property {string} name - Base family name.
 * @property {Record<string, string>} members - Map of shapes to block identifiers.
 */
/**
 * Deterministically constructs and exports the block family catalog.
 *
 * @param {FamilyBuilderOptions} [options={}] - Builder options.
 * @returns {object} The parsed and validated block family catalog.
 */
export function generateBlockFamilies(options = {}) {
  const stagingBase = path.resolve(options.stagingBase || '_temp');
  const catalogPath = path.resolve(
    options.catalogPath || path.join(stagingBase, 'block_families.json')
  );
  const builder = new BlockFamilyBuilder({
    stagingBase,
    stagingDir: options.stagingDir,
    sourceDir: options.sourceDir,
    templateDir: options.templateDir,
    catalogPath,
  });
  if (options.requireExisting && !fs.existsSync(catalogPath)) {
    throw new Error(`Missing block family catalog: '${catalogPath}' not found.`);
  }

  return builder.build();
}

/**
 * Bedrock block family metadata catalog builder.
 */
export class BlockFamilyBuilder {
  /**
   * Initializes the family builder with directory paths.
   *
   * @param {FamilyBuilderOptions} [options={}] - Configuration options.
   */
  constructor(options = {}) {
    this.stagingBase = path.resolve(options.stagingBase || '_temp');
    this.stagingDir = path.resolve(options.stagingDir || path.join(this.stagingBase, 'behavior_pack'));
    this.sourceDir = path.resolve(options.sourceDir || 'packs/behavior_pack');
    this.templateDir = path.resolve(options.templateDir || 'templates');
    this.catalogPath = path.resolve(options.catalogPath || path.join(this.stagingBase, 'block_families.json'));
    this.expander = new TemplateExpander(this.templateDir);
  }

  /**
   * Scans a directory recursively for JSON files.
   *
   * @param {string} dir - Directory to scan.
   * @returns {string[]} List of full file paths.
   */
  collectJsonFiles(dir) {
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
    return results.sort();
  }

  /**
   * Identifies the primary shape classification of a block.
   *
   * @param {string} identifier - Block identifier.
   * @param {Record<string, any>} blockObj - Parsed minecraft:block object.
   * @returns {string} Shape identifier such as base, slab, stair, wall.
   */
  determineShape(identifier, blockObj) {
    const cleanId = identifier.toLowerCase();
    if (cleanId.endsWith('_slab') || cleanId.includes('slab')) {
      return 'slab';
    }
    if (cleanId.endsWith('_stair') || cleanId.endsWith('_stairs') || cleanId.includes('stair')) {
      return 'stair';
    }
    if (cleanId.endsWith('_wall') || cleanId.includes('wall')) {
      return 'wall';
    }
    if (cleanId.endsWith('_fence') || cleanId.includes('fence')) {
      return 'fence';
    }

    const components = blockObj.components || {};
    if (components['minecraft:geometry']) {
      const geo = String(
        typeof components['minecraft:geometry'] === 'object'
          ? components['minecraft:geometry'].identifier
          : components['minecraft:geometry']
      ).toLowerCase();
      if (geo.includes('stair')) {
        return 'stair';
      }
      if (geo.includes('slab')) {
        return 'slab';
      }
    }

    return 'base';
  }

  /**
   * Extracts family names associated with a block.
   *
   * @param {string} identifier - Full block identifier.
   * @param {Record<string, any>} blockObj - Parsed minecraft:block object.
   * @returns {string[]} Unique list of family names.
   */
  extractFamilies(identifier, blockObj) {
    const families = new Set();
    const components = blockObj.components || {};

    if (components['minecraft:block_families']) {
      const declared = components['minecraft:block_families'];
      if (Array.isArray(declared)) {
        declared.forEach((fam) => families.add(String(fam).trim()));
      } else if (typeof declared === 'string') {
        families.add(declared.trim());
      }
    }

    for (const key of Object.keys(components)) {
      if (key.startsWith('tag:family_')) {
        families.add(key.replace('tag:family_', '').trim());
      }
    }

    const colonIndex = identifier.indexOf(':');
    const localName = colonIndex !== -1 ? identifier.slice(colonIndex + 1) : identifier;
    const strippedName = localName
      .replace(/_slab$/, '')
      .replace(/_stairs?$/, '')
      .replace(/_wall$/, '')
      .replace(/_fence$/, '')
      .replace(/_block$/, '');

    if (strippedName) {
      families.add(strippedName);
    }

    return Array.from(families).filter(Boolean).sort();
  }

  /**
   * Extracts tags from block component definitions.
   *
   * @param {Record<string, any>} blockObj - Parsed minecraft:block object.
   * @returns {string[]} Unique list of tags.
   */
  extractTags(blockObj) {
    const tags = new Set();
    const components = blockObj.components || {};
    for (const key of Object.keys(components)) {
      if (key.startsWith('tag:')) {
        tags.add(key.replace('tag:', '').trim());
      }
    }
    return Array.from(tags).sort();
  }

  /**
   * Discovers and parses block definitions from available directories.
   *
   * @returns {Array<{ identifier: string, shape: string, families: string[], tags: string[], filePath: string }>}
   */
  discoverBlocks() {
    const stagedBlocksDir = path.join(this.stagingDir, 'blocks');
    const sourceBlocksDir = path.join(this.sourceDir, 'blocks');
    const targetDir = fs.existsSync(stagedBlocksDir) ? stagedBlocksDir : sourceBlocksDir;

    const files = this.collectJsonFiles(targetDir);
    const discovered = [];

    for (const file of files) {
      let content = fs.readFileSync(file, 'utf-8');
      const relPath = path.relative(targetDir, file);

      if (this.expander.isTemplate(content)) {
        try {
          content = this.expander.expand(content, relPath);
        } catch {
          continue;
        }
      }

      let parsed;
      try {
        parsed = JSON.parse(content);
      } catch {
        continue;
      }

      const blockDef = parsed['minecraft:block'];
      if (!blockDef || !blockDef.description || !blockDef.description.identifier) {
        continue;
      }

      const identifier = blockDef.description.identifier;
      const shape = this.determineShape(identifier, blockDef);
      const families = this.extractFamilies(identifier, blockDef);
      const tags = this.extractTags(blockDef);

      discovered.push({
        identifier,
        shape,
        families,
        tags,
        filePath: relPath.replace(/\\/g, '/'),
      });
    }

    return discovered.sort((a, b) => a.identifier.localeCompare(b.identifier));
  }

  /**
   * Generates catalog payload from discovered block entries.
   *
   * @returns {object} Full catalog object.
   */
  compileCatalog() {
    const blocks = this.discoverBlocks();
    const families = {};
    const blockToFamily = {};
    const shapeCounts = {};

    for (const block of blocks) {
      shapeCounts[block.shape] = (shapeCounts[block.shape] || 0) + 1;

      for (const fam of block.families) {
        if (!families[fam]) {
          families[fam] = {
            name: fam,
            base: null,
            members: {},
            blocks: [],
            tags: [],
          };
        }

        const familyEntry = families[fam];
        familyEntry.members[block.shape] = block.identifier;

        if (!familyEntry.blocks.includes(block.identifier)) {
          familyEntry.blocks.push(block.identifier);
        }

        if (block.shape === 'base' || !familyEntry.base) {
          familyEntry.base = block.identifier;
        }

        for (const tag of block.tags) {
          if (!familyEntry.tags.includes(tag)) {
            familyEntry.tags.push(tag);
          }
        }

        if (!blockToFamily[block.identifier]) {
          blockToFamily[block.identifier] = fam;
        }
      }
    }

    const sortedFamilies = {};
    for (const famKey of Object.keys(families).sort()) {
      const fam = families[famKey];
      fam.blocks.sort();
      fam.tags.sort();
      sortedFamilies[famKey] = fam;
    }

    const catalogBody = {
      format_version: '1.20.80',
      families: sortedFamilies,
      block_to_family: blockToFamily,
      statistics: {
        total_families: Object.keys(sortedFamilies).length,
        total_blocks: blocks.length,
        shape_counts: shapeCounts,
      },
    };

    const serialized = JSON.stringify(catalogBody, null, 2);
    const checksum = crypto.createHash('sha256').update(serialized).digest('hex');

    return {
      ...catalogBody,
      checksum,
    };
  }

  /**
   * Writes compiled catalog to disk deterministically.
   *
   * @returns {object} Written catalog object.
   */
  build() {
    const catalog = this.compileCatalog();
    const serialized = JSON.stringify(catalog, null, 2) + '\n';

    fs.mkdirSync(path.dirname(this.catalogPath), { recursive: true });
    fs.writeFileSync(this.catalogPath, serialized, 'utf-8');

    if (fs.existsSync(this.stagingDir)) {
      const stagedCatalog = path.join(this.stagingDir, 'block_families.json');
      fs.writeFileSync(stagedCatalog, serialized, 'utf-8');
    }

    return catalog;
  }
}

if (process.argv[1] && process.argv[1].endsWith('family_builder.js')) {
  try {
    const catalog = generateBlockFamilies();
    console.log(`[FamilyBuilder] Catalog successfully built: ${catalog.statistics.total_families} families (${catalog.statistics.total_blocks} blocks).`);
  } catch (err) {
    console.error(`[FamilyBuilder][Error] ${err.message}`);
    process.exit(1);
  }
}
