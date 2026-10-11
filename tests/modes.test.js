const SaaSMode = require('../src/modes/saas');
const StandardMode = require('../src/modes/standard');
const DemoMode = require('../src/modes/demo');
const modeRegistry = require('../src/modes');

describe('Mode System', () => {
  describe('SaaSMode', () => {
    let saasMode;

    beforeEach(() => {
      saasMode = new SaaSMode();
      saasMode.enable();
    });

    test('should enable SaaS mode', () => {
      expect(saasMode.enabled).toBe(true);
      expect(saasMode.name).toBe('saas');
    });

    test('should register a tenant', () => {
      const tenant = saasMode.registerTenant('tenant-1', 'basic');
      expect(tenant).toBeDefined();
      expect(tenant.id).toBe('tenant-1');
      expect(tenant.tier).toBe('basic');
      expect(tenant.active).toBe(true);
    });

    test('should default to free tier', () => {
      const tenant = saasMode.registerTenant('tenant-2');
      expect(tenant.tier).toBe('free');
    });

    test('should get tenant', () => {
      saasMode.registerTenant('tenant-3');
      const tenant = saasMode.getTenant('tenant-3');
      expect(tenant).not.toBeNull();
      expect(tenant.id).toBe('tenant-3');
    });

    test('should check feature access', () => {
      saasMode.registerTenant('tenant-4', 'premium');
      expect(saasMode.hasFeature('tenant-4', 'analytics')).toBe(true);
      expect(saasMode.hasFeature('tenant-4', 'api_access')).toBe(true);
    });

    test('should list tenants', () => {
      saasMode.registerTenant('tenant-5');
      saasMode.registerTenant('tenant-6');
      const tenants = saasMode.listTenants();
      expect(tenants).toHaveLength(2);
    });

    test('should upgrade tier', () => {
      saasMode.registerTenant('tenant-7', 'free');
      const upgraded = saasMode.upgradeTier('tenant-7', 'premium');
      expect(upgraded.tier).toBe('premium');
    });

    test('should throw on invalid tier', () => {
      expect(() => saasMode.registerTenant('tenant-8', 'invalid-tier'))
        .toThrow('Invalid tier: invalid-tier');
    });

    test('should throw on maximum tenant limit', () => {
      for (let i = 0; i < 1000; i++) {
        saasMode.registerTenant(`tenant-${i}`, 'free');
      }
      expect(() => saasMode.registerTenant('overflow-tenant'))
        .toThrow('Maximum tenant limit reached');
    });
  });

  describe('StandardMode', () => {
    test('should enable', () => {
      const mode = new StandardMode();
      mode.enable();
      expect(mode.enabled).toBe(true);
    });
  });

  describe('DemoMode', () => {
    test('should enable', () => {
      const mode = new DemoMode();
      mode.enable();
      expect(mode.enabled).toBe(true);
    });
  });

  describe('ModeRegistry', () => {
    test('should list available modes', () => {
      const modes = modeRegistry.listModes();
      expect(modes).toHaveLength(3);
      expect(modes.map(m => m.name)).toContain('standard');
      expect(modes.map(m => m.name)).toContain('saas');
      expect(modes.map(m => m.name)).toContain('demo');
    });

    test('should switch to SaaS mode', () => {
      const mode = modeRegistry.setMode('saas');
      expect(modeRegistry.currentMode).toBe('saas');
      expect(mode.name).toBe('saas');
    });

    test('should throw on invalid mode', () => {
      expect(() => modeRegistry.setMode('invalid-mode'))
        .toThrow('Mode not found: invalid-mode');
    });
  });
});
