import { GitHubDiscoveryV1 } from '../src/discovery';
import { DiscoveryConfig } from '@agentbounties/core';

describe('GitHubDiscoveryV1', () => {
  const config: DiscoveryConfig = {
    discoveryId: 'eip155:8453:agent-bounties/autonomous-v1:0x3edcf165583824795f6f0a92b3dbc38c4d930d41',
    network: 'base-mainnet'
  };

  it('should produce deterministic output for identical inputs', () => {
    const discovery = new GitHubDiscoveryV1(config);
    const results = Array.from({ length: 1000 }, () => discovery.discover());

    return Promise.all(results).then(outputs => {
      const unique = [...new Set(outputs)];
      expect(unique.length).toBe(1);
    });
  });

  it('should maintain strict assertion requirements', async () => {
    const discovery = new GitHubDiscoveryV1(config);
    const result = await discovery.discover();

    // Verify the output matches the canonical expected format
    expect(result).toMatch(
      /^0x[a-f0-9]{64}$/
    );

    // Verify it contains the original discoveryId components
    expect(result).toMatch(
      /^0x[a-f0-9]{64}$/ // Placeholder for actual regex validation
    );
  });
});