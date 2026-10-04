<content>
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Generate directory if it doesn't exist
const keysDir = path.join(__dirname, '../keys');
if (!fs.existsSync(keysDir)) {
  fs.mkdirSync(keysDir);
}

// Generate RSA key pair
function generateKeyPair() {
  return crypto.generateKeyPairSync('rsa', {
    modulusLength: 2048,
    publicKeyEncoding: {
      type: 'spki',
      format: 'pem'
    },
    privateKeyEncoding: {
      type: 'pkcs8',
      format: 'pem'
    }
  });
}

// Generate keys for services
const keys = {
  key1: generateKeyPair(),
  key2: generateKeyPair(),
  'service-a': generateKeyPair(),
  'service-b': generateKeyPair()
};

// Save keys to files
Object.entries(keys).forEach(([name, keyPair]) => {
  fs.writeFileSync(path.join(keysDir, `${name}.pem`), keyPair.publicKey);
  fs.writeFileSync(path.join(keysDir, `${name}_private.pem`), keyPair.privateKey);
  console.log(`Generated ${name} key pair`);
});

console.log('Keys generated successfully');