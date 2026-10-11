/**
 * Standard Mode for Bounty Plaza
 * Default single-instance operating mode
 */

class StandardMode {
  constructor() {
    this.name = 'standard';
    this.description = 'Standard Mode - Single instance, shared resources';
    this.enabled = false;
  }

  enable() {
    this.enabled = true;
    console.log('[Standard] Mode enabled');
    return this;
  }
}

module.exports = StandardMode;
