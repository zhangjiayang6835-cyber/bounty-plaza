import * as fs from 'fs';
import * as path from 'path';
import { TemplateExpander } from './template_expander.js';
import { PackValidator } from './pack_validator.js';
import { syncDirectory, resolveMojangDevelopmentPath } from './sync.js';

/**
 * Configuration options for the Bedrock build pipeline.
 *
 * @typedef {object} BuildPipelineOptions
 * @property {string} [sourceDir='packs/behavior_pack'] - Directory containing source pack files.
 * @property {string} [stagingDir='_temp/behavior_pack'] - Isolated directory for staging expanded templates.
 * @property {string} [templateDir='templates'] - Directory containing template fragments.
 * @property {string} [destDir] - Target deployment directory.
 * @property {boolean} [clean=true] - Whether to perform a clean-slate wipe before build.
 * @property {boolean} [deploy=false] - Whether to deploy to com.mojang development folder.
 */

/**
 * Bedrock pack build and prebuild asset pipeline orchestrator.
 */
export class BuildPipeline {
  /**
   * Initializes the pipeline with user or default options.
   *
   * @param {BuildPipelineOptions} [options={}] - Pipeline options.
   */
  constructor(options = {}) {
    this.sourceDir = path.resolve(options.sourceDir || 'packs/behavior_pack');
    this.stagingBase = path.resolve('_temp');
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

    return { expandedCount, copiedCount };
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
    if (this.cleanSlate) {
      this.clean();
    }

    const stagingStats = this.stageAndExpand();

    const validationReport = this.validate();
    if (!validationReport.valid) {
      const errorMessage = validationReport.errors.join('\n');
      throw new Error(`Pack validation failed in staging:\n${errorMessage}`);
    }

    const syncStats = this.synchronize();

    return {
      success: true,
      stats: {
        staging: stagingStats,
        validation: {
          fileCount: validationReport.fileCount,
          blockCount: validationReport.blockCount,
        },
        sync: syncStats,
        destDir: this.destDir,
      },
    };
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

  const pipeline = new BuildPipeline({ deploy, destDir });
  try {
    const result = pipeline.run();
    console.log(
      `[BuildPipeline] Success: Expanded ${result.stats.staging.expandedCount} templates, ` +
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
