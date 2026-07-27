const DodgeRoll = require('../mechanics/dodgeRoll');

class PlayerController {
  constructor(player, config = {}) {
    this.player = player;
    this.dodgeRoll = new DodgeRoll(config.dodgeConfig || {});
    this.inputHandler = config.inputHandler || {};
    this.position = { x: 0, y: 0 };
    this.velocity = { x: 0, y: 0 };
  }

  /**
   * Handle dodge roll input
   * @param {Object} direction - Direction to dodge {x, y}
   * @returns {boolean} True if dodge was initiated
   */
  handleDodgeInput(direction) {
    if (this.dodgeRoll.initiate(direction)) {
      this.onDodgeStart();
      return true;
    }
    return false;
  }

  /**
   * Update player state
   * @param {number} deltaTime - Time elapsed in seconds
   */
  update(deltaTime) {
    const dodgeState = this.dodgeRoll.update(deltaTime);

    if (dodgeState.isActive) {
      this.velocity = dodgeState.velocity;
      this.player.setInvulnerable(dodgeState.isInvulnerable);
    } else {
      this.velocity = { x: 0, y: 0 };
      this.player.setInvulnerable(false);
    }

    this.position.x += this.velocity.x * deltaTime;
    this.position.y += this.velocity.y * deltaTime;

    this.player.setPosition(this.position);
  }

  /**
   * Called when dodge starts
   */
  onDodgeStart() {
    if (this.player.onDodgeStart) {
      this.player.onDodgeStart();
    }
  }

  /**
   * Get current dodge state
   * @returns {Object} Dodge state information
   */
  getDodgeState() {
    return {
      isActive: this.dodgeRoll.isActive,
      canDodge: this.dodgeRoll.canDodge(),
      remainingCooldown: this.dodgeRoll.getRemainingCooldown(),
      isInvulnerable: this.dodgeRoll.isInvulnerable()
    };
  }
}

module.exports = PlayerController;