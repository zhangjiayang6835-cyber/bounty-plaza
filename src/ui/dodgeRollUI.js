class DodgeRollUI {
  constructor(config = {}) {
    this.containerSelector = config.containerSelector || '#dodge-ui';
    this.cooldownBarSelector = config.cooldownBarSelector || '.dodge-cooldown-bar';
    this.statusTextSelector = config.statusTextSelector || '.dodge-status';
    this.container = document.querySelector(this.containerSelector);
    this.cooldownBar = document.querySelector(this.cooldownBarSelector);
    this.statusText = document.querySelector(this.statusTextSelector);
    this.maxCooldown = config.maxCooldown || 1.0;
  }

  /**
   * Update UI based on dodge state
   * @param {Object} dodgeState - State from getDodgeState()
   */
  update(dodgeState) {
    if (!this.container) return;

    this.updateCooldownBar(dodgeState);
    this.updateStatusText(dodgeState);
    this.updateVisibility(dodgeState);
  }

  /**
   * Update cooldown bar display
   * @param {Object} dodgeState - Dodge state
   */
  updateCooldownBar(dodgeState) {
    if (!this.cooldownBar) return;

    const percentage = (1 - dodgeState.remainingCooldown / this.maxCooldown) * 100;
    this.cooldownBar.style.width = `${Math.max(0, Math.min(100, percentage))}%`;
  }

  /**
   * Update status text display
   * @param {Object} dodgeState - Dodge state
   */
  updateStatusText(dodgeState) {
    if (!this.statusText) return;

    if (dodgeState.isActive) {
      this.statusText.textContent = 'DODGING';
      this.statusText.classList.add('active');
    } else if (!dodgeState.canDodge) {
      const cooldown = dodgeState.remainingCooldown.toFixed(1);
      this.statusText.textContent = `COOLDOWN: ${cooldown}s`;
      this.statusText.classList.remove('active');
    } else {
      this.statusText.textContent = 'READY';
      this.statusText.classList.add('ready');
    }
  }

  /**
   * Update visibility based on state
   * @param {Object} dodgeState - Dodge state
   */
  updateVisibility(dodgeState) {
    if (!this.container) return;

    if (dodgeState.isInvulnerable) {
      this.container.classList.add('invulnerable');
    } else {
      this.container.classList.remove('invulnerable');
    }
  }

  /**
   * Show dodge effect animation
   */
  showDodgeEffect() {
    if (!this.container) return;
    this.container.classList.add('dodge-effect');
    setTimeout(() => {
      this.container.classList.remove('dodge-effect');
    }, 300);
  }
}

module.exports = DodgeRollUI;