const fs = require('fs');
const path = require('path');
const { extractZip } = require('../src/utils/extractZip');
const AdmZip = require('adm-zip');

describe('Zip Slip Vulnerability Protection', () => {
  const testDir = path.join(__dirname, 'temp');
  const maliciousZipPath = path.join(testDir, 'malicious.zip');
  const safeZipPath = path.join(testDir, 'safe.zip');

  beforeAll(() => {
    // Create test directory
    if (!fs.existsSync(testDir)) {
      fs.mkdirSync(testDir, { recursive: true });
    }

    // Create a safe zip file
    const safeZip = new AdmZip();
    safeZip.addFile('safe.txt', Buffer.from('This is safe content'));
    safeZip.writeZip(safeZipPath);

    // Create a malicious zip file with path traversal
    const maliciousZip = new AdmZip();
    maliciousZip.addFile('../../etc/cron.d/malicious', Buffer.from('Malicious cron job'));
    maliciousZip.writeZip(maliciousZipPath);
  });

  afterAll(() => {
    // Clean up test files
    if (fs.existsSync(testDir)) {
      fs.rmSync(testDir, { recursive: true, force: true });
    }
  });

  test('should safely extract a normal zip file', async () => {
    const extractDir = path.join(testDir, 'extract-safe');
    await expect(extractZip(safeZipPath, extractDir)).resolves.not.toThrow();
    
    // Check that the file was extracted correctly
    const extractedFile = path.join(extractDir, 'safe.txt');
    expect(fs.existsSync(extractedFile)).toBe(true);
    
    // Check that no other files were created
    const files = fs.readdirSync(extractDir);
    expect(files).toHaveLength(1);
  });

  test('should detect and reject zip slip attack', async () => {
    const extractDir = path.join(testDir, 'extract-malicious');
    await expect(extractZip(maliciousZipPath, extractDir)).rejects.toThrow(
      'Entry ../../etc/cron.d/malicious is outside of target directory'
    );
    
    // Check that no files were extracted
    expect(fs.existsSync(extractDir)).toBe(false);
  });

  test('should reject entries with .. in the path', async () => {
    const extractDir = path.join(testDir, 'extract-dotdot');
    
    // Create a zip with .. in the filename
    const dotdotZip = new AdmZip();
    dotdotZip.addFile('file/../malicious.txt', Buffer.from('Malicious content'));
    const dotdotZipPath = path.join(testDir, 'dotdot.zip');
    dotdotZip.writeZip(dotdotZipPath);
    
    await expect(extractZip(dotdotZipPath, extractDir)).rejects.toThrow(
      'Path traversal detected in entry: file/../malicious.txt'
    );
    
    // Clean up
    fs.unlinkSync(dotdotZipPath);
  });
});