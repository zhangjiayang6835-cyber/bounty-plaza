/**
 * Mode Registry for Bounty Plaza
 * Manages different operating modes: standard, saas, demo
 */

const StandardMode = require('./standard');
const SaaSMode = require('./saas');
const DemoMode = require('./demo');

class ModeRegistry {
  constructor() {
    this.modes = {
      standard: new StandardMode(),
      saas: new SaaSMode(),
      demo: new DemoMode()
    };
    this.currentMode = 'standard';
  }

  setMode(modeName) {
    const mode = this.modes[modeName];
    if (!mode) {
      throw new Error(`Mode not found: ${modeName}`);
    }
    this.currentMode = modeName;
    if (mode.enable) {
      mode.enable();
    }
    console.log(`[Mode] Switched to ${modeName} mode`);
    return mode;
  }

  getMode(name) {
    return this.modes[name] || null;
  }

  getCurrentMode() {
    return this.modes[this.currentMode];
  }

  listModes() {
    return Object.keys(this.modes).map(name => ({
      name,
      description: this.modes[name].description || 'No description'
    }));
  }
}

module.exports = new ModeRegistry();
