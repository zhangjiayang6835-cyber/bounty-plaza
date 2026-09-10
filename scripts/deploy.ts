import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

/**
 * Resolve Bedrock development directory with Windows 11 support.
 * Handles both UWP package paths and modern Win32 roaming paths.
 */
function resolveBedrocDir(): string | null {
  const platform = process.platform;
  
  if (platform === 'win32') {
    // Windows: try modern roaming path first, fallback to UWP
    const username = process.env.USERNAME || os.userInfo().username;
    const roamingPath = path.join(
      'C:', 'Users', username,
      'AppData', 'Roaming', '.minecraft', 'development_behavior_packs'
    );
    
    if (fs.existsSync(roamingPath)) {
      return roamingPath;
    }
    
    // Fallback: UWP package path
    const uwpPath = path.join(
      'C:', 'Users', username,
      'AppData', 'Local', 'Packages',
      'Microsoft.MinecraftUWP_8wekyb3d8bbwe', 'LocalState',
      'games', 'com.mojang', 'development_behavior_packs'
    );
    
    if (fs.existsSync(uwpPath)) {
      return uwpPath;
    }
    
    // Neither path exists
    return null;
  } else if (platform === 'darwin') {
    // macOS
    const home = os.homedir();
    return path.join(home, 'Library', 'Application Support',
      'minecraft', 'development_behavior_packs');
  } else if (platform === 'linux') {
    // Linux
    const home = os.homedir();
    return path.join(home, '.minecraft', 'development_behavior_packs');
  }
  
  return null;
}

/**
 * Deploy behavior packs to development directory.
 * Gracefully handles missing destination directory.
 */
export async function deploy(): Promise<void> {
  const srcDir = path.join(__dirname, '..', 'behavior_packs');
  const destDir = resolveBedrocDir();
  
  if (!destDir) {
    console.warn(
      '⚠️  WARNING: Bedrock development directory not found.\n' +
      '   Skipping deployment. Ensure Minecraft is installed and development paths are configured.'
    );
    return;
  }
  
  // Ensure destination exists (create if needed)
  if (!fs.existsSync(destDir)) {
    console.log(`Creating development directory: ${destDir}`);
    try {
      fs.mkdirSync(destDir, { recursive: true });
    } catch (err) {
      console.error(`❌ Failed to create directory: ${err}`);
      process.exit(1);
    }
  }
  
  // Ensure source exists
  if (!fs.existsSync(srcDir)) {
    console.error(`❌ Source directory not found: ${srcDir}`);
    process.exit(1);
  }
  
  // Copy behavior packs
  try {
    const packs = fs.readdirSync(srcDir);
    for (const pack of packs) {
      const srcPack = path.join(srcDir, pack);
      const destPack = path.join(destDir, pack);
      
      console.log(`📦 Deploying: ${pack}`);
      copyDirRecursive(srcPack, destPack);
    }
    console.log('✅ Deployment successful!');
  } catch (err) {
    console.error(`❌ Deployment failed: ${err}`);
    process.exit(1);
  }
}

/**
 * Recursively copy directory.
 */
function copyDirRecursive(src: string, dest: string): void {
  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }
  
  const files = fs.readdirSync(src);
  for (const file of files) {
    const srcFile = path.join(src, file);
    const destFile = path.join(dest, file);
    const stat = fs.statSync(srcFile);
    
    if (stat.isDirectory()) {
      copyDirRecursive(srcFile, destFile);
    } else {
      fs.copyFileSync(srcFile, destFile);
    }
  }
}

// Execute if called directly
if (require.main === module) {
  deploy().catch(err => {
    console.error(err);
    process.exit(1);
  });
}
