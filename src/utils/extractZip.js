const fs = require('fs');
const path = require('path');
const { promisify } = require('util');
const extract = promisify(require('extract-zip'));

/**
 * Safely extracts a zip file to a destination directory
 * @param {string} zipPath - Path to the zip file
 * @param {string} destDir - Destination directory
 * @returns {Promise<void>}
 */
async function extractZip(zipPath, destDir) {
  // Ensure destination directory exists
  if (!fs.existsSync(destDir)) {
    fs.mkdirSync(destDir, { recursive: true });
  }

  // Get absolute canonical path of destination directory
  const canonicalDestDir = path.resolve(destDir);

  try {
    await extract(zipPath, { 
      dir: canonicalDestDir,
      onEntry: (entry) => {
        // Get the full path of the entry
        const entryPath = path.join(canonicalDestDir, entry.path);
        
        // Get canonical path of the entry
        const canonicalEntryPath = path.resolve(entryPath);
        
        // Check if the canonical entry path starts with the canonical destination directory
        if (!canonicalEntryPath.startsWith(canonicalDestDir + path.sep)) {
          throw new Error(`Entry ${entry.path} is outside of target directory`);
        }
        
        // Check for path traversal attempts
        if (entry.path.includes('..')) {
          throw new Error(`Path traversal detected in entry: ${entry.path}`);
        }
      }
    });
  } catch (err) {
    if (err.message.includes('is outside of target directory') || 
        err.message.includes('Path traversal detected')) {
      throw new Error(`Zip extraction failed: ${err.message}`);
    }
    throw err;
  }
}

module.exports = { extractZip };