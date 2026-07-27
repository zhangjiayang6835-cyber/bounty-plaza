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
    this.rollDirection = { x: 0, y: 0 };
    this.rollStartTime = 0;
    this.rollStartPosition = { x: 0, y: 0 };
    this.onRollStart = config.onRollStart || (() => {});
    this.onRollEnd = config.onRollEnd || (() => {});
    this.onRollUpdate = config.onRollUpdate || (() => {});
  }

  /**
   * Initiates a dodge roll in the specified direction
   * @param {Object} direction - Direction vector {x, y}
   * @param {Object} currentPosition - Current position {x, y}
   * @returns {boolean} - Whether the roll was successfully initiated
   */
  initiateRoll(direction, currentPosition) {
    const currentTime = Date.now() / 1000;
    
    // Check if roll is on cooldown
    if (this.isRolling) {
      return false;
    }

    if (currentTime - this.lastRollTime < this.rollCooldown) {
      return false;
    }

    // Validate direction
    if (!direction || typeof direction.x !== 'number' || typeof direction.y !== 'number') {
      return false;
    }

    // Normalize direction vector
    const magnitude = Math.sqrt(direction.x ** 2 + direction.y ** 2);
    if (magnitude === 0) {
      return false;
    }

    this.rollDirection = {
      x: direction.x / magnitude,
      y: direction.y / magnitude
    };

    this.isRolling = true;
    this.rollStartTime = currentTime;
    this.rollStartPosition = { ...currentPosition };
    this.lastRollTime = currentTime;

    this.onRollStart({
      direction: this.rollDirection,
      startPosition: this.rollStartPosition
    });

    return true;
  }

  /**
   * Updates the dodge roll state and returns new position
   * @param {Object} currentPosition - Current position {x, y}
   * @returns {Object} - Updated position {x, y, isRolling}
   */
  update(currentPosition) {
    if (!this.isRolling) {
      return { ...currentPosition, isRolling: false };
    }

    const currentTime = Date.now() / 1000;
    const elapsedTime = currentTime - this.rollStartTime;
    const progress = Math.min(elapsedTime / this.rollDuration, 1);

    // Calculate distance traveled
    const distance = this.rollSpeed * elapsedTime;
    const newPosition = {
      x: this.rollStartPosition.x + this.rollDirection.x * distance,
      y: this.rollStartPosition.y + this.rollDirection.y * distance
    };

    this.onRollUpdate({
      position: newPosition,
      progress: progress,
      direction: this.rollDirection
    });

    // Check if roll is complete
    if (progress >= 1) {
      this.isRolling = false;
      this.onRollEnd({
        finalPosition: newPosition,
        direction: this.rollDirection
      });
    }

    return {
      ...newPosition,
      isRolling: this.isRolling,
      progress: progress
    };
  }

  /**
   * Cancels the current dodge roll
   * @returns {boolean} - Whether a roll was cancelled
   */
  cancelRoll() {
    if (!this.isRolling) {
      return false;
    }

    this.isRolling = false;
    this.onRollEnd({
      cancelled: true,
      direction: this.rollDirection
    });

    return true;
  }

  /**
   * Gets the current roll state
   * @returns {Object} - Current state information
   */
  getState() {
    const currentTime = Date.now() / 1000;
    const cooldownRemaining = Math.max(
      0,
      this.rollCooldown - (currentTime - this.lastRollTime)
    );

    return {
      isRolling: this.isRolling,
      cooldownRemaining: cooldownRemaining,
      rollDirection: { ...this.rollDirection },
      rollStartPosition: { ...this.rollStartPosition }
    };
  }

  /**
   * Resets the dodge roll system
   */
  reset() {
    this.isRolling = false;
    this.lastRollTime = 0;
    this.rollDirection = { x: 0, y: 0 };
    this.rollStartTime = 0;
    this.rollStartPosition = { x: 0, y: 0 };
  }
}

module.exports = DodgeRoll;