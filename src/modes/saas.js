/**
 * SaaS Mode for Bounty Plaza
 * Provides multi-tenant Software as a Service functionality
 */

class SaaSMode {
  constructor() {
    this.name = 'saas';
    this.description = 'SaaS Mode - Multi-tenant bounty platform';
    this.enabled = false;
    this.tenants = new Map();
    this.config = {
      subscription tiers: ['free', 'basic', 'premium', 'enterprise'],
      maxTenants: 1000,
      features: {
        free: ['basic_bounties', 'public_discussions'],
        basic: ['basic_bounties', 'public_discussions', 'private_bounties'],
        premium: ['basic_bounties', 'public_discussions', 'private_bounties', 'analytics', 'api_access'],
        enterprise: ['all']
      }
    };
  }

  enable() {
    this.enabled = true;
    console.log('[SaaS] Mode enabled');
    return this;
  }

  registerTenant(tenantId, tier = 'free') {
    if (this.tenants.size >= this.config.maxTenants) {
      throw new Error('Maximum tenant limit reached');
    }
    if (!this.config.features[tier]) {
      throw new Error(`Invalid tier: ${tier}`);
    }
    this.tenants.set(tenantId, {
      id: tenantId,
      tier,
      createdAt: new Date().toISOString(),
      active: true
    });
    console.log(`[SaaS] Tenant ${tenantId} registered with tier ${tier}`);
    return this.tenants.get(tenantId);
  }

  unregisterTenant(tenantId) {
    const tenant = this.tenants.get(tenantId);
    if (!tenant) {
      throw new Error(`Tenant not found: ${tenantId}`);
    }
    tenant.active = false;
    this.tenants.delete(tenantId);
    console.log(`[SaaS] Tenant ${tenantId} unregistered`);
    return tenant;
  }

  getTenant(tenantId) {
    return this.tenants.get(tenantId) || null;
  }

  hasFeature(tenantId, feature) {
    const tenant = this.tenants.get(tenantId);
    if (!tenant) return false;
    const allowed = this.config.features[tenant.tier];
    return allowed.includes(feature) || (Array.isArray(allowed) && allowed.includes('all'));
  }

  listTenants() {
    return Array.from(this.tenants.values());
  }

  upgradeTier(tenantId, newTier) {
    const tenant = this.tenants.get(tenantId);
    if (!tenant) {
      throw new Error(`Tenant not found: ${tenantId}`);
    }
    if (!this.config.features[newTier]) {
      throw new Error(`Invalid tier: ${newTier}`);
    }
    tenant.tier = newTier;
    console.log(`[SaaS] Tenant ${tenantId} upgraded to ${newTier}`);
    return tenant;
  }
}

module.exports = SaaSMode;
