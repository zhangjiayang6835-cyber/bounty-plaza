import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { ExecutionMode, SaaSModeManager, TenantTier } from '../src/saas_mode.js';

describe('SaaS Mode Node.js Runtime', () => {
  test('should default to SaaS execution mode and support switching', () => {
    const mgr = new SaaSModeManager();
    assert.equal(mgr.isSaaSMode(), true);

    mgr.setMode(ExecutionMode.STANDALONE);
    assert.equal(mgr.isSaaSMode(), false);
  });

  test('should register tenant and retrieve configuration', () => {
    const mgr = new SaaSModeManager();
    const tenant = mgr.registerTenant('t-100', 'Omni Corp', TenantTier.PRO);
    assert.equal(tenant.tenantId, 't-100');
    assert.equal(tenant.name, 'Omni Corp');
    assert.equal(tenant.tier, TenantTier.PRO);

    const fetched = mgr.getTenant('t-100');
    assert.equal(fetched.name, 'Omni Corp');
  });

  test('should enforce multi-tenant project isolation', () => {
    const mgr = new SaaSModeManager();
    mgr.registerTenant('t-1', 'Org 1');
    mgr.registerTenant('t-2', 'Org 2');

    mgr.createProject('t-1', 'p-alpha', 2048);
    const p1 = mgr.getProject('t-1', 'p-alpha');
    assert.equal(p1.projectId, 'p-alpha');

    assert.throws(() => {
      mgr.getProject('t-2', 'p-alpha');
    }, /not found in tenant t-2/);
  });

  test('should enforce free tier project limits', () => {
    const mgr = new SaaSModeManager();
    mgr.registerTenant('t-free', 'Free Org', TenantTier.FREE);

    mgr.createProject('t-free', 'p1');
    mgr.createProject('t-free', 'p2');
    mgr.createProject('t-free', 'p3');

    assert.throws(() => {
      mgr.createProject('t-free', 'p4');
    }, /Project limit 3 exceeded/);
  });

  test('should bypass limits in standalone mode', () => {
    const mgr = new SaaSModeManager(ExecutionMode.STANDALONE);
    const project = mgr.createProject('any', 'standalone_p');
    assert.equal(project.projectId, 'standalone_p');
    assert.equal(project.tenantId, 'standalone_tenant');
  });
});
