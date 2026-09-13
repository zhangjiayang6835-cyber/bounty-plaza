/**
 * @fileoverview Multi-tenant SaaS mode runtime manager for Node.js and browser environments.
 */

export const ExecutionMode = Object.freeze({
  STANDALONE: 'standalone',
  SAAS: 'saas'
});

export const TenantTier = Object.freeze({
  FREE: 'free',
  PRO: 'pro',
  ENTERPRISE: 'enterprise'
});

export const TierLimits = Object.freeze({
  [TenantTier.FREE]: Object.freeze({
    maxProjects: 3,
    maxStorageBytes: 100 * 1024 * 1024,
    allowsWebhooks: false,
    allowsCustomDomains: false
  }),
  [TenantTier.PRO]: Object.freeze({
    maxProjects: 50,
    maxStorageBytes: 10 * 1024 * 1024 * 1024,
    allowsWebhooks: true,
    allowsCustomDomains: true
  }),
  [TenantTier.ENTERPRISE]: Object.freeze({
    maxProjects: 10000,
    maxStorageBytes: 1024 * 1024 * 1024 * 1024,
    allowsWebhooks: true,
    allowsCustomDomains: true
  })
});

/**
 * Manages SaaS mode execution state, tenant configurations, and quota validation.
 */
export class SaaSModeManager {
  /**
   * Initializes SaaS mode manager with target execution mode.
   * @param {string} mode Initial mode, defaults to ExecutionMode.SAAS.
   */
  constructor(mode = ExecutionMode.SAAS) {
    this.mode = mode;
    this.tenants = new Map();
    this.projects = new Map();
  }

  /**
   * Returns true if active execution mode is multi-tenant SaaS.
   * @returns {boolean}
   */
  isSaaSMode() {
    return this.mode === ExecutionMode.SAAS;
  }

  /**
   * Switches runtime execution mode.
   * @param {string} mode Target execution mode.
   */
  setMode(mode) {
    this.mode = mode;
  }

  /**
   * Registers a new tenant organization.
   * @param {string} tenantId Unique tenant identifier.
   * @param {string} name Organization name.
   * @param {string} tier Subscription tier.
   * @returns {Object} Created tenant object.
   */
  registerTenant(tenantId, name, tier = TenantTier.FREE) {
    const tenant = {
      tenantId,
      name,
      tier,
      createdAt: Date.now()
    };
    this.tenants.set(tenantId, tenant);
    if (!this.projects.has(tenantId)) {
      this.projects.set(tenantId, new Map());
    }
    return tenant;
  }

  /**
   * Retrieves registered tenant.
   * @param {string} tenantId Tenant identifier.
   * @returns {Object} Tenant metadata.
   */
  getTenant(tenantId) {
    const tenant = this.tenants.get(tenantId);
    if (!tenant) {
      throw new Error(`Tenant ${tenantId} not found`);
    }
    return tenant;
  }

  /**
   * Creates a project respecting tenant isolation and tier limits.
   * @param {string} tenantId Tenant identifier.
   * @param {string} projectId Project identifier.
   * @param {number} storageBytes Project storage consumption.
   * @returns {Object} Created project metadata.
   */
  createProject(tenantId, projectId, storageBytes = 1024) {
    if (this.mode === ExecutionMode.STANDALONE) {
      return { projectId, tenantId: 'standalone_tenant', storageBytes };
    }

    const tenant = this.getTenant(tenantId);
    const limits = TierLimits[tenant.tier];
    const tenantProjects = this.projects.get(tenantId);

    if (tenantProjects.size >= limits.maxProjects) {
      throw new Error(`Project limit ${limits.maxProjects} exceeded for tier ${tenant.tier}`);
    }

    const project = {
      projectId,
      tenantId,
      storageBytes,
      createdAt: Date.now()
    };
    tenantProjects.set(projectId, project);
    return project;
  }

  /**
   * Retrieves project within isolated tenant partition.
   * @param {string} tenantId Tenant identifier.
   * @param {string} projectId Project identifier.
   * @returns {Object} Project metadata.
   */
  getProject(tenantId, projectId) {
    if (this.mode === ExecutionMode.STANDALONE) {
      return { projectId, mode: 'standalone' };
    }

    const tenantProjects = this.projects.get(tenantId);
    if (!tenantProjects || !tenantProjects.has(projectId)) {
      throw new Error(`Project ${projectId} not found in tenant ${tenantId}`);
    }
    return tenantProjects.get(projectId);
  }
}
