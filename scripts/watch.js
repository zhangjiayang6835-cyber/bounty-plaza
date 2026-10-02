const fs = require('fs').promises;
const path = require('path');
const compiler = require('../compiler');

let fileMtimes = {};

async function initialBuild(sourceDir, destDir) {
  const entries = await fs.readdir(sourceDir, { withFileTypes: true });
  
  for (const entry of entries) {
    const sourcePath = path.join(sourceDir, entry.name);
    const destPath = path.join(destDir, entry.name);
    
    if (entry.isFile()) {
      await processFile(sourcePath, destPath);
      fileMtimes[sourcePath] = (await fs.stat(sourcePath)).mtimeMs;
    } else if (entry.isDirectory()) {
      await fs.mkdir(destPath, { recursive: true });
      await initialBuild(sourcePath, destPath);
    }
  }
}

async function processFile(sourcePath, destPath) {
  try {
    const ext = path.extname(sourcePath);
    
    if (ext === '.jsonte') {
      const content = await fs.readFile(sourcePath, 'utf8');
      const compiled = compiler.compile(content);
      await fs.writeFile(destPath, compiled);
    } else {
      await fs.copyFile(sourcePath, destPath);
    }
  } catch (err) {
    console.error(`Error processing ${sourcePath}:`, err);
  }
}

async function watchFiles(sourceDir, destDir) {
  await initialBuild(sourceDir, destDir);
  
  const watcher = fs.watch(sourceDir, { recursive: true }, async (eventType, fileName) => {
    const sourcePath = path.join(sourceDir, fileName);
    const destPath = path.join(destDir, fileName);
    
    if (eventType === 'rename') {
      // Handle file rename/move
      await fs.rm(destPath, { recursive: true, force: true });
      await processFile(sourcePath, destPath);
      return;
    }
    
    const currentMtime = (await fs.stat(sourcePath)).mtimeMs;
    
    if (fileMtimes[sourcePath] !== currentMtime) {
      fileMtimes[sourcePath] = currentMtime;
      await processFile(sourcePath, destPath);
    }
  });
}

if (require.main === module) {
  const sourceDir = path.join(__dirname, '../source');
  const destDir = path.join(__dirname, '../game');
  
  watchFiles(sourceDir, destDir)
    .catch(err => console.error('Watch error:', err));
}