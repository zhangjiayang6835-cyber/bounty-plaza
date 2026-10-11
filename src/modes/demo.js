/**
 * Demo Mode for Bounty Plaza
 * Read-only mode for demonstrations and testing
 */

class DemoMode {
  constructor() {
    this.name = 'demo';
    this.description = 'Demo Mode - Read-only, pre-populated data';
    this.enabled = false;
  }

  enable() {
    this.enabled = true;
    console.log('[Demo] Mode enabled');
    return this;
  }
}

module.exports = DemoMode;
