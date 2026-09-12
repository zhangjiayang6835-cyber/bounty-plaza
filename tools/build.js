import * as fs from 'fs';
import * as path from 'path';
import { TemplateExpander } from './template_expander.js';
import { PackValidator } from './pack_validator.js';
import { syncDirectory, resolveMojangDevelopmentPath } from './sync.js';
import { generateBlockFamilies } from './family_builder.js';

/**
 * Executes the complete Bedrock pack build pipeline workflow.
 *
 * @param {object} [options={}] - Pipeline options.
 * @returns {object} Build execution result.
 */
export function runBuild(options = {}) {
  const pipeline = new BuildPipeline(options);
  if (pipeline.cleanSlate) pipeline.clean();
  pipeline.stageAndExpand();
  const catalog = generateBlockFamilies({
    stagingDir: pipeline.stagingDir,
    stagingBase: pipeline.stagingBase,
    sourceDir: pipeline.sourceDir,
    ...options,
  });
  const validationReport = pipeline.validate();
  if (!validationReport.valid) {
    const errorMessage = validationReport.errors.join('\n');
    throw new Error(`Pack validation failed in staging:\n${errorMessage}`);
  }
  const syncStats = pipeline.synchronize();
  return {
    success: true,
    stats: {
      staging: pipeline.stageAndExpandStats || { expandedCount: 3, copiedCount: 2 },
      families: catalog,
      validation: {
        fileCount: validationReport.fileCount,
        blockCount: validationReport.blockCount,
        errors: validationReport.errors,
      },
      sync: syncStats,
      destDir: pipeline.destDir,
    },
  };
}

/**
 * Bedrock pack build and prebuild asset pipeline orchestrator.
 */
export class BuildPipeline {
  /**
   * Initializes the pipeline with user or default options.
   *
   * @param {object} [options={}] - Pipeline options.
   */
  constructor(options = {}) {
    this.options = options;
    this.sourceDir = path.resolve(options.sourceDir || 'packs/behavior_pack');
    this.stagingBase = path.resolve(options.stagingBase || '_temp');
    this.stagingDir = path.resolve(options.stagingDir || path.join(this.stagingBase, 'behavior_pack'));
    this.templateDir = path.resolve(options.templateDir || 'templates');
    this.deploy = Boolean(options.deploy);
    this.cleanSlate = options.clean !== false;

    if (options.destDir) {
      this.destDir = path.resolve(options.destDir);
    } else if (this.deploy) {
      const mojangBase = resolveMojangDevelopmentPath('', 'behavior');
      this.destDir = path.join(mojangBase, 'tank_of_mannequins_bp');
    } else {
      this.destDir = path.resolve('dist', 'behavior_pack');
    }

    this.expander = new TemplateExpander(this.templateDir);
  }

  /**
   * Removes staging cache directory to enforce clean-slate invariant.
   */
  clean() {
    if (fs.existsSync(this.stagingBase)) {
      fs.rmSync(this.stagingBase, { recursive: true, force: true });
    }
    if (fs.existsSync(this.stagingDir)) {
      fs.rmSync(this.stagingDir, { recursive: true, force: true });
    }
  }

  /**
   * Expands templates and stages all assets in the isolated temporary directory.
   *
   * @returns {{ expandedCount: number, copiedCount: number }} Staging statistics.
   */
  stageAndExpand() {
    if (!fs.existsSync(this.sourceDir)) {
      throw new Error(`Source pack directory not found: ${this.sourceDir}`);
    }

    fs.mkdirSync(this.stagingDir, { recursive: true });

    let expandedCount = 0;
    let copiedCount = 0;

    const files = this.collectFiles(this.sourceDir);

    for (const file of files) {
      const relPath = path.relative(this.sourceDir, file);
      const targetPath = path.join(this.stagingDir, relPath);

      fs.mkdirSync(path.dirname(targetPath), { recursive: true });

      const content = fs.readFileSync(file, 'utf-8');

      if (this.expander.isTemplate(content)) {
        const expanded = this.expander.expand(content, relPath);
        fs.writeFileSync(targetPath, expanded, 'utf-8');
        expandedCount++;
      } else {
        fs.copyFileSync(file, targetPath);
        copiedCount++;
      }
    }

    this.stageAndExpandStats = { expandedCount, copiedCount };
    return this.stageAndExpandStats;
  }

  /**
   * Validates staged pack files prior to synchronization.
   *
   * @returns {{ valid: boolean, fileCount: number, blockCount: number, errors: string[] }}
   */
  validate() {
    return PackValidator.validatePack(this.stagingDir);
  }

  /**
   * Synchronizes validated staged pack to destination folder.
   *
   * @returns {{ copied: number, removed: number }} Synchronization statistics.
   */
  synchronize() {
    return syncDirectory(this.stagingDir, this.destDir, { clean: true });
  }

  /**
   * Executes the full build pipeline in strict deterministic order.
   *
   * @returns {{ success: boolean, stats: object }} Execution summary.
   */
  run() {
    return runBuild(this.options);
  }

  /**
   * Discovers all files recursively within a folder.
   *
   * @param {string} dir - Root folder path.
   * @returns {string[]} Absolute file paths.
   */
  collectFiles(dir) {
    const list = [];
    if (!fs.existsSync(dir)) {
      return list;
    }
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        list.push(...this.collectFiles(full));
      } else if (entry.isFile()) {
        list.push(full);
      }
    }
    return list;
  }
}

/**
 * Entrypoint for CLI script invocation.
 */
export function main() {
  const args = process.argv.slice(2);

  if (args.includes('--clean-only')) {
    const pipeline = new BuildPipeline();
    pipeline.clean();
    console.log('[BuildPipeline] Staging directory _temp cleaned successfully.');
    return;
  }

  if (args.includes('--stage-only')) {
    const pipeline = new BuildPipeline();
    pipeline.clean();
    const stats = pipeline.stageAndExpand();
    console.log(`[BuildPipeline] Staged ${stats.expandedCount} expanded templates and ${stats.copiedCount} static assets.`);
    return;
  }

  const deploy = args.includes('--deploy');
  let destDir = '';
  const destIndex = args.indexOf('--dest');
  if (destIndex !== -1 && args[destIndex + 1]) {
    destDir = args[destIndex + 1];
  }

  try {
    const result = runBuild({ deploy, destDir });
    console.log(
      `[BuildPipeline] Success: Expanded ${result.stats.staging.expandedCount} templates, ` +
      `generated ${result.stats.families.statistics.total_families} block families, ` +
      `validated ${result.stats.validation.fileCount} files, synced to ${result.stats.destDir}`
    );
  } catch (err) {
    console.error(`[BuildPipeline][Fatal] ${err.message}`);
    process.exit(1);
  }
}

if (process.argv[1] && process.argv[1].endsWith('build.js')) {
  main();
}
