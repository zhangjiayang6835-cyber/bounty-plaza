const fs = require('fs');
const path = require('path');
const { deployBounty } = require('@agent-bounties/sdk'); // Hypothetical platform SDK

async function seedBounty() {
  const configPath = path.join(__dirname, '../config/bounties/api-child-bounty.json');
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  
  console.log(`Seeding bounty: ${config.title} with ${config.total_funding} USDC`);
  
  const result = await deployBounty({
    ...config,
    network: config.network,
    verifierModule: config.verifier
  });

  console.log('Bounty seeded successfully. Wait for canonical BountySettled receipt.');
  return result;
}

seedBounty().catch(console.error);
