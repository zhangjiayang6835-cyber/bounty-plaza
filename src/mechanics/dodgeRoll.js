/**
 * Dodge Rolling Mechanic
 * Implements a dodge roll system for character movement and evasion
 */

class DodgeRoll {
  constructor(config = {}) {
    this.isRolling = false;
    this.rollDuration = config.rollDuration || 0.5; // seconds
    this.rollSpeed = config.rollSpeed || 15; // units per second
    this.rollCooldown = config.rollCooldown || 1.0; // seconds
    this.lastRollTime = 0;
    this.rollStartTime = 0;
    this.rollDirection = { x: 0, y: 0 };
    this.iFrames = config.iFrames || 0.3; // invulnerability frames in seconds
    this.isInvulnerable = false;
    this.onRollStart = config.onRollStart || (() => {});
    this.onRollEnd = config.onRollEnd || (() => {});
    this.onRollUpdate = config.onRollUpdate || (() => {});
  }

  /**
   * Attempt to start a dodge roll
   * @param {Object} direction - Direction vector {x, y}
   * @param {number} currentTime - Current game time in seconds
   * @returns {boolean} - Whether roll was successfully initiated
   */
  attemptRoll(direction, currentTime = Date.now() / 1000) {
    // Check if already rolling
    if (this.isRolling) {
      return false;
    }

    // Check cooldown
    if (currentTime - this.lastRollTime < this.rollCooldown) {
      return false;
    }

    // Validate direction
    if (!direction || (direction.x === 0 && direction.y === 0)) {
      return false;
    }

    // Normalize direction
    const length = Math.sqrt(direction.x ** 2 + direction.y ** 2);
    this.rollDirection = {
      x: direction.x / length,
      y: direction.y / length
    };

    this.isRolling = true;
    this.rollStartTime = currentTime;
    this.lastRollTime = currentTime;
    this.isInvulnerable = true;

    this.onRollStart({
      direction: this.rollDirection,
      timestamp: currentTime
    });

    return true;
  }

  /**
   * Update dodge roll state
   * @param {number} currentTime - Current game time in seconds
   * @returns {Object} - Roll state and movement vector
   */
  update(currentTime = Date.now() / 1000) {
    if (!this.isRolling) {
      return {
        isRolling: false,
        isInvulnerable: false,
        movement: { x: 0, y: 0 },
        progress: 0
      };
    }

    const elapsedTime = currentTime - this.rollStartTime;
    const progress = Math.min(elapsedTime / this.rollDuration, 1);

    // Calculate movement with easing (ease-out cubic)
    const easeProgress = 1 - Math.pow(1 - progress, 3);
    const movement = {
      x: this.rollDirection.x * this.rollSpeed * easeProgress,
      y: this.rollDirection.y * this.rollSpeed * easeProgress
    };

    // Check if invulnerability frames have ended
    if (elapsedTime > this.iFrames) {
      this.isInvulnerable = false;
    }

    // Check if roll is complete
    if (progress >= 1) {
      this.isRolling = false;
      this.onRollEnd({
        totalDistance: this.rollSpeed * this.rollDuration,
        timestamp: currentTime
      });
    }

    this.onRollUpdate({
      progress,
      movement,
      isInvulnerable: this.isInvulnerable,
      timestamp: currentTime
    });

    return {
      isRolling: this.isRolling,
      isInvulnerable: this.isInvulnerable,
      movement,
      progress
    };
  }

  /**
   * Get current roll state
   * @returns {Object} - Current state
   */
  getState() {
    return {
      isRolling: this.isRolling,
      isInvulnerable: this.isInvulnerable,
      rollDirection: { ...this.rollDirection },
      progress: this.isRolling ? (Date.now() / 1000 - this.rollStartTime) / this.rollDuration : 0
    };
  }

  /**
   * Cancel current roll
   */
  cancel() {
    if (this.isRolling) {
      this.isRolling = false;
      this.isInvulnerable = false;
      this.onRollEnd({
        totalDistance: 0,
        cancelled: true,
        timestamp: Date.now() / 1000
      });
    }
  }

  /**
   * Reset dodge roll state
   */
  reset() {
    this.isRolling = false;
    this.isInvulnerable = false;
    this.lastRollTime = 0;
    this.rollStartTime = 0;
    this.rollDirection = { x: 0, y: 0 };
  }

  /**
   * Get cooldown remaining
   * @param {number} currentTime - Current game time
   * @returns {number} - Seconds remaining on cooldown
   */
  getCooldownRemaining(currentTime = Date.now() / 1000) {
    const timeSinceLastRoll = currentTime - this.lastRollTime;
    return Math.max(0, this.rollCooldown - timeSinceLastRoll);
  }

  /**
   * Check if dodge roll is available
   * @param {number} currentTime - Current game time
   * @returns {boolean}
   */
  isAvailable(currentTime = Date.now() / 1000) {
    return !this.isRolling && this.getCooldownRemaining(currentTime) === 0;
  }
}

module.exports = DodgeRoll;