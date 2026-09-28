const fs = require('fs');
const path = require('path');
const chokidar = require('chokidar');
const { compileJsonte } = require('../source/compiler/jsonte');

const SOURCE_DIR = path.join(__dirname, '../source');
const GAME_DIR = path.join(__dirname, '../game');

// Track file modification times for incremental compilation
const fileMtimes = new Map();

// Process a single file through the JSONTE compiler if needed
async function processFile(filePath) {
  const relativePath = path.relative(SOURCE_DIR, filePath);
  const outputPath = path.join(GAME_DIR, relativePath);

  // Skip binary files
  if (path.extname(filePath) === '.png' || path.extname(filePath) === '.ogg') {
    await fs.promises.mkdir(path.dirname(outputPath), { recursive: true });
    await fs.promises.copyFile(filePath, outputPath);
    return;
  }

  // Skip non-JSONTE files
  if (path.extname(filePath) !== '.jsonte') {
    await fs.promises.mkdir(path.dirname(outputPath), { recursive: true });
    await fs.promises.copyFile(filePath, outputPath);
    return;
  }

  // Check if file needs recompilation
  const stats = await fs.promises.stat(filePath);
  const lastMtime = fileMtimes.get(filePath);
  if (lastMtime && lastMtime >= stats.mtimeMs) {
    return;
  }

  // Compile JSONTE file
  const content = await fs.promises.readFile(filePath, 'utf8');
  const compiled = compileJsonte(content);

  // Write output
  await fs.promises.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.promises.writeFile(outputPath, compiled);

  // Update modification time
  fileMtimes.set(filePath, Date.now());
}

// Watch for file changes
chokidar.watch(SOURCE_DIR, {
  ignored: /(^|[/\\])\../, // ignore dotfiles
  persistent: true,
  ignoreInitial: true,
}).on('all', async (event, filePath) => {
  if (event === 'add' || event === 'change') {
    try {
      await processFile(filePath);
      console.log(`Processed: ${filePath}`);
    } catch (err) {
      console.error(`Error processing ${filePath}:`, err);
    }
  } else if (event === 'unlink') {
    const relativePath = path.relative(SOURCE_DIR, filePath);
    const outputPath = path.join(GAME_DIR, relativePath);
    try {
      await fs.promises.unlink(outputPath);
      fileMtimes.delete(filePath);
      console.log(`Removed: ${outputPath}`);
    } catch (err) {
      console.error(`Error removing ${outputPath}:`, err);
    }
  }
});

// Initial build
async function initialBuild() {
  const files = await fs.promises.readdir(SOURCE_DIR, { recursive: true });
  for (const file of files) {
    const filePath = path.join(SOURCE_DIR, file);
    const stats = await fs.promises.stat(filePath);
    if (stats.isFile()) {
      try {
        await processFile(filePath);
      } catch (err) {
        console.error(`Error processing ${filePath}:`, err);
      }
    }
  }
}

initialBuild().then(() => {
  console.log('Initial build complete');
});