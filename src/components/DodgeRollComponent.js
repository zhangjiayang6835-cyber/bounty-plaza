/**
 * Dodge Roll Component for Game Entities
 * Integrates dodge roll mechanic with entity physics and rendering
 */

const DodgeRoll = require('../mechanics/dodgeRoll');

class DodgeRollComponent {
  constructor(entity, config = {}) {
    this.entity = entity;
    this.dodgeRoll = new DodgeRoll({
      rollDuration: config.rollDuration || 0.5,
      rollSpeed: config.rollSpeed || 15,
      rollCooldown: config.rollCooldown || 1.0,
      iFrames: config.iFrames || 0.3,
      onRollStart: this.onRollStart.bind(this),
      onRollEnd: this.onRollEnd.bind(this),
      onRollUpdate: this.onRollUpdate.bind(this)
    });

    this.rollTrail = [];
    this.maxTrailLength = config.maxTrailLength || 10;
    this.showTrail = config.showTrail !== false;
  }

  /**
   * Attempt to initiate dodge roll
   * @param {Object} direction - Direction to roll
   * @returns {boolean}
   */
  roll(direction) {
    const currentTime = Date.now() / 1000;
    return this.dodgeRoll.attemptRoll(direction, currentTime);
  }

  /**
   * Update component state
   * @param {number} deltaTime - Time since last update in seconds
   */
  update(deltaTime) {
    const currentTime = Date.now() / 1000;
    const state = this.dodgeRoll.update(currentTime);

    if (state.isRolling && this.entity) {
      // Apply movement to entity
      if (this.entity.position) {
        this.entity.position.x += state.movement.x * deltaTime;
        this.entity.position.y += state.movement.y * deltaTime;
      }

      // Add to trail for visual effect
      if (this.showTrail && this.entity.position) {
        this.rollTrail.push({
          x: this.entity.position.x,
          y: this.entity.position.y,
          alpha: 1 - state.progress,
          timestamp: currentTime
        });

        if (this.rollTrail.length > this.maxTrailLength) {
          this.rollTrail.shift();
        }
      }
    } else {
      this.rollTrail = [];
    }
  }

  /**
   * Render dodge roll visual effects
   * @param {Object} renderer - Rendering context
   */
  render(renderer) {
    if (!this.showTrail || this.rollTrail.length === 0) {
      return;
    }

    // Draw trail
    this.rollTrail.forEach((point, index) => {
      const alpha = point.alpha * (index / this.rollTrail.length);
      renderer.drawCircle(point.x, point.y, 5, {
        fillStyle: `rgba(100, 150, 255, ${alpha * 0.5})`,
        strokeStyle: `rgba(100, 150, 255, ${alpha})`
      });
    });
  }

  /**
   * Called when roll starts
   */
  onRollStart(data) {
    if (this.entity && this.entity.onDodgeRollStart) {
      this.entity.onDodgeRollStart(data);
    }
  }

  /**
   * Called when roll ends
   */
  onRollEnd(data) {
    this.rollTrail = [];
    if (this.entity && this.entity.onDodgeRollEnd) {
      this.entity.onDodgeRollEnd(data);
    }
  }

  /**
   * Called on each roll update
   */
  onRollUpdate(state) {
    if (this.entity && this.entity.onDodgeRollUpdate) {
      this.entity.onDodgeRollUpdate(state);
    }
  }

  /**
   * Check if entity is currently rolling
   * @returns {boolean}
   */
  isRolling() {
    return this.dodgeRoll.isRolling;
  }

  /**
   * Check if entity is invulnerable
   * @returns {boolean}
   */
  isInvulnerable() {
    return this.dodgeRoll.isInvulnerable;
  }

  /**
   * Check if roll is available
   * @returns {boolean}
   */
  canRoll() {
    return this.dodgeRoll.isAvailable();
  }

  /**
   * Get time until next roll is available
   * @returns {number}
   */
  getTimeUntilAvailable() {
    return this.dodgeRoll.getTimeUntilAvailable();
  }

  /**
   * Cancel current roll
   */
  cancel() {
    this.dodgeRoll.cancel();
    this.rollTrail = [];
  }

  /**
   * Reset component state
   */
  reset() {
    this.dodgeRoll.reset();
    this.rollTrail = [];
  }
}

module.exports = DodgeRollComponent;
