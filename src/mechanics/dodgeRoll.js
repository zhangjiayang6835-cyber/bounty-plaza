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
   * Attempt to initiate a dodge roll
   * @param {Object} direction - Direction to roll { x, y }
   * @param {number} currentTime - Current game time in seconds
   * @returns {boolean} - Whether roll was successfully initiated
   */
  attemptRoll(direction, currentTime = Date.now() / 1000) {
    if (!direction || typeof direction.x !== 'number' || typeof direction.y !== 'number') {
      console.warn('Invalid direction provided to dodge roll');
      return false;
    }

    if (this.isRolling) {
      return false;
    }

    if (currentTime - this.lastRollTime < this.rollCooldown) {
      return false;
    }

    // Normalize direction
    const magnitude = Math.sqrt(direction.x ** 2 + direction.y ** 2);
    if (magnitude === 0) {
      console.warn('Cannot roll in zero direction');
      return false;
    }

    this.rollDirection = {
      x: direction.x / magnitude,
      y: direction.y / magnitude
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
   * @returns {Object} - Roll state and movement delta
   */
  update(currentTime = Date.now() / 1000) {
    const state = {
      isRolling: this.isRolling,
      isInvulnerable: this.isInvulnerable,
      movement: { x: 0, y: 0 },
      progress: 0
    };

    if (!this.isRolling) {
      return state;
    }

    const elapsedTime = currentTime - this.rollStartTime;
    const progress = Math.min(elapsedTime / this.rollDuration, 1);

    state.progress = progress;

    // Calculate movement with easing (ease-out cubic)
    const easeProgress = 1 - Math.pow(1 - progress, 3);
    const distance = this.rollSpeed * this.rollDuration * easeProgress;

    state.movement = {
      x: this.rollDirection.x * distance,
      y: this.rollDirection.y * distance
    };

    // Check if roll is complete
    if (progress >= 1) {
      this.isRolling = false;
      this.onRollEnd({
        timestamp: currentTime,
        totalDistance: this.rollSpeed * this.rollDuration
      });
    }

    // Check if invulnerability frames are complete
    if (this.isInvulnerable && elapsedTime >= this.iFrames) {
      this.isInvulnerable = false;
    }

    this.onRollUpdate(state);

    return state;
  }

  /**
   * Cancel current dodge roll
   */
  cancel() {
    if (this.isRolling) {
      this.isRolling = false;
      this.isInvulnerable = false;
      this.onRollEnd({
        timestamp: Date.now() / 1000,
        cancelled: true
      });
    }
  }

  /**
   * Get current roll progress (0-1)
   * @returns {number}
   */
  getProgress() {
    if (!this.isRolling) {
      return 0;
    }
    const currentTime = Date.now() / 1000;
    const elapsed = currentTime - this.rollStartTime;
    return Math.min(elapsed / this.rollDuration, 1);
  }

  /**
   * Get time until next roll is available
   * @returns {number} - Seconds until roll is available
   */
  getTimeUntilAvailable() {
    const currentTime = Date.now() / 1000;
    const timeSinceLastRoll = currentTime - this.lastRollTime;
    const timeRemaining = this.rollCooldown - timeSinceLastRoll;
    return Math.max(0, timeRemaining);
  }

  /**
   * Check if dodge roll is currently available
   * @returns {boolean}
   */
  isAvailable() {
    return !this.isRolling && this.getTimeUntilAvailable() === 0;
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
}

module.exports = DodgeRoll;