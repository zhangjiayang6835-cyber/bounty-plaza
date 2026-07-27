/**
 * Dodge Roll Controller
 * Manages dodge roll input and integration with game entities
 */

const DodgeRoll = require('./dodgeRoll');

class DodgeRollController {
  constructor(entity, config = {}) {
    this.entity = entity;
    this.dodgeRoll = new DodgeRoll(config);
    this.inputBuffer = { x: 0, y: 0 };
    this.isEnabled = true;
  }

  /**
   * Handles dodge roll input
   * @param {Object} direction - Direction vector {x, y}
   * @param {number} currentTime - Current game time
   * @returns {boolean} - Whether roll was initiated
   */
  handleDodgeInput(direction, currentTime) {
    if (!this.isEnabled) {
      return false;
    }

    return this.dodgeRoll.initiateRoll(direction, currentTime);
  }

  /**
   * Updates dodge roll and applies movement to entity
   * @param {number} deltaTime - Time since last frame in seconds
   * @param {number} currentTime - Current game time
   */
  update(deltaTime, currentTime) {
    if (!this.isEnabled || !this.entity) {
      return;
    }

    const movement = this.dodgeRoll.update(currentTime);

    if (movement.x !== 0 || movement.y !== 0) {
      this.applyMovement(movement, deltaTime);
    }
  }

  /**
   * Applies movement to the entity
   * @param {Object} movement - Movement vector
   * @param {number} deltaTime - Delta time
   */
  applyMovement(movement, deltaTime) {
    if (!this.entity.position) {
      return;
    }

    this.entity.position.x += movement.x * deltaTime;
    this.entity.position.y += movement.y * deltaTime;

    if (this.entity.onMove) {
      this.entity.onMove(this.entity.position);
    }
  }

  /**
   * Gets invulnerability status
   * @returns {boolean}
   */
  isInvulnerable() {
    return this.dodgeRoll.getIsInvulnerable();
  }

  /**
   * Gets rolling status
   * @returns {boolean}
   */
  isRolling() {
    return this.dodgeRoll.getIsRolling();
  }

  /**
   * Gets cooldown remaining
   * @param {number} currentTime - Current game time
   * @returns {number}
   */
  getCooldownRemaining(currentTime) {
    return this.dodgeRoll.getCooldownRemaining(currentTime);
  }

  /**
   * Checks if roll can be performed
   * @param {number} currentTime - Current game time
   * @returns {boolean}
   */
  canRoll(currentTime) {
    return this.dodgeRoll.canRoll(currentTime);
  }

  /**
   * Enables/disables dodge rolling
   * @param {boolean} enabled
   */
  setEnabled(enabled) {
    this.isEnabled = enabled;
    if (!enabled && this.dodgeRoll.getIsRolling()) {
      this.dodgeRoll.endRoll();
    }
  }

  /**
   * Resets the controller
   */
  reset() {
    this.dodgeRoll.reset();
    this.inputBuffer = { x: 0, y: 0 };
  }
}

module.exports = DodgeRollController;