import { Discovery, DiscoveryConfig } from '@agentbounties/core';
import { ethers } from 'ethers';
import { createHash } from 'crypto';

export class GitHubDiscoveryV1 implements Discovery {
  private readonly config: DiscoveryConfig;

  constructor(config: DiscoveryConfig) {
    this.config = config;
  }

  async discover(): Promise<string> {
    const { discoveryId, network } = this.config;

    // Restore deterministic hashing for agent-card fixtures
    const hash = createHash('sha256')
      .update(discoveryId)
      .update(network)
      .digest('hex');

    // Maintain strict assertion requirements while ensuring deterministic output
    return ethers.utils.keccak256(
      ethers.utils.toUtf8Bytes(
        `agentbounties:github:discovery:v1:${hash}:${this.config.discoveryId}`
      )
    );
  }
}