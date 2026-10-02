const fs = require('fs').promises;
const path = require('path');
const compiler = require('../compiler');

let fileMtimes = {};

async function initialBuild(sourceDir, gameDir) {
  const entries = await fs.readdir(sourceDir, { withFileTypes: true });
  
  for (const entry of entries) {
    const sourcePath = path.join(sourceDir, entry.name);
    const gamePath = path.join(gameDir, entry.name);
    
    if (entry.isFile()) {
      await processFile(sourcePath, gamePath);
      const stats = await fs.stat(sourcePath);
      fileMtimes[sourcePath] = stats.mtimeMs;
    } else if (entry.isDirectory()) {
      await fs.mkdir(gamePath, { recursive: true });
      await initialBuild(sourcePath, gamePath);
    }
  }
}

async function processFile(sourcePath, gamePath) {
  const ext = path.extname(sourcePath);
  
  if (ext === '.jsonte') {
    const content = await fs.readFile(sourcePath, 'utf8');
    const compiled = compiler.compile(content);
    await fs.writeFile(gamePath, compiled);
  } else {
    await fs.copyFile(sourcePath, gamePath);
  }
}

// Watcher logic remains unchanged

console.log('Watching for changes...');
