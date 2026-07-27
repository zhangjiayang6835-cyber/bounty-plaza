/**
 * Dodge Roll Component for Game Entities
 * Integrates dodge roll mechanic with entity physics and animation
 */

const DodgeRoll = require('../mechanics/dodgeRoll');

class DodgeRollComponent {
  constructor(entity, config = {}) {
    this.entity = entity;
    this.dodgeRoll = new DodgeRoll(config);
    this.animationController = config.animationController || null;
    this.particleEmitter = config.particleEmitter || null;
    this.soundManager = config.soundManager || null;
    this.isEnabled = true;

    this.setupCallbacks();
  }

  /**
   * Setup dodge roll callbacks
   */
  setupCallbacks() {
    this.dodgeRoll.onRollStart = (data) => this.handleRollStart(data);
    this.dodgeRoll.onRollEnd = (data) => this.handleRollEnd(data);
    this.dodgeRoll.onRollUpdate = (data) => this.handleRollUpdate(data);
  }

  /**
   * Handle roll start
   */
  handleRollStart(data) {
    if (!this.isEnabled) return;

    // Play animation
    if (this.animationController) {
      this.animationController.play('dodge_roll', {
        duration: this.dodgeRoll.rollDuration,
        direction: data.direction
      });
    }

    // Emit particles
    if (this.particleEmitter) {
      this.particleEmitter.emit('dodge_roll_start', {
        position: this.entity.position,
        direction: data.direction
      });
    }

    // Play sound
    if (this.soundManager) {
      this.soundManager.play('dodge_roll', { volume: 0.7 });
    }

    // Update entity state
    this.entity.isDodging = true;
    this.entity.isInvulnerable = true;
  }

  /**
   * Handle roll end
   */
  handleRollEnd(data) {
    if (!this.isEnabled) return;

    this.entity.isDodging = false;
    this.entity.isInvulnerable = false;

    if (this.animationController) {
      this.animationController.stop('dodge_roll');
    }
  }

  /**
   * Handle roll update
   */
  handleRollUpdate(data) {
    if (!this.isEnabled) return;

    // Apply movement
    if (this.entity.velocity) {
      this.entity.velocity.x = data.movement.x / (1 / 60); // Assuming 60 FPS
      this.entity.velocity.y = data.movement.y / (1 / 60);
    }

    // Update invulnerability state
    this.entity.isInvulnerable = data.isInvulnerable;

    // Emit particles during roll
    if (this.particleEmitter && data.progress % 0.1 < 0.016) {
      this.particleEmitter.emit('dodge_roll_trail', {
        position: this.entity.position,
        progress: data.progress
      });
    }
  }

  /**
   * Attempt to perform a dodge roll
   * @param {Object} direction - Direction vector
   * @returns {boolean}
   */
  performDodgeRoll(direction) {
    if (!this.isEnabled) {
      return false;
    }

    return this.dodgeRoll.attemptRoll(direction, Date.now() / 1000);
  }

  /**
   * Update component
   * @param {number} deltaTime - Time since last update in seconds
   */
  update(deltaTime) {
    if (!this.isEnabled) return;

    const currentTime = Date.now() / 1000;
    this.dodgeRoll.update(currentTime);
  }

  /**
   * Get component state
   */
  getState() {
    return {
      isRolling: this.dodgeRoll.isRolling,
      isInvulnerable: this.dodgeRoll.isInvulnerable,
      cooldownRemaining: this.dodgeRoll.getCooldownRemaining(),
      isAvailable: this.dodgeRoll.isAvailable(),
      rollProgress: this.dodgeRoll.getState().progress
    };
  }

  /**
   * Enable/disable component
   */
  setEnabled(enabled) {
    this.isEnabled = enabled;
    if (!enabled) {
      this.dodgeRoll.cancel();
    }
  }

  /**
   * Reset component
   */
  reset() {
    this.dodgeRoll.reset();
    this.entity.isDodging = false;
    this.entity.isInvulnerable = false;
  }
}

module.exports = DodgeRollComponent;
