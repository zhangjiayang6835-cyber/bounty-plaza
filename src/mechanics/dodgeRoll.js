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
   * Initiates a dodge roll in the specified direction
   * @param {Object} direction - Direction vector {x, y}
   * @param {number} currentTime - Current game time in seconds
   * @returns {boolean} - Whether the roll was successfully initiated
   */
  initiateRoll(direction, currentTime = Date.now() / 1000) {
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
    const magnitude = Math.sqrt(direction.x ** 2 + direction.y ** 2);
    this.rollDirection = {
      x: direction.x / magnitude,
      y: direction.y / magnitude
    };

    this.isRolling = true;
    this.rollStartTime = currentTime;
    this.isInvulnerable = true;
    this.onRollStart(this.rollDirection);

    return true;
  }

  /**
   * Updates the dodge roll state
   * @param {number} currentTime - Current game time in seconds
   * @returns {Object} - Movement vector for this frame
   */
  update(currentTime = Date.now() / 1000) {
    const movement = { x: 0, y: 0 };

    if (!this.isRolling) {
      return movement;
    }

    const elapsedTime = currentTime - this.rollStartTime;
    const rollProgress = elapsedTime / this.rollDuration;

    if (rollProgress >= 1.0) {
      this.endRoll(currentTime);
      return movement;
    }

    // Calculate movement for this frame
    const frameDistance = this.rollSpeed * (this.rollDuration / 60); // Assuming 60 FPS base
    movement.x = this.rollDirection.x * frameDistance;
    movement.y = this.rollDirection.y * frameDistance;

    // Check if invulnerability frames have expired
    if (elapsedTime > this.iFrames && this.isInvulnerable) {
      this.isInvulnerable = false;
    }

    this.onRollUpdate({
      progress: rollProgress,
      movement,
      isInvulnerable: this.isInvulnerable
    });

    return movement;
  }

  /**
   * Ends the current dodge roll
   * @param {number} currentTime - Current game time in seconds
   */
  endRoll(currentTime = Date.now() / 1000) {
    if (!this.isRolling) {
      return;
    }

    this.isRolling = false;
    this.isInvulnerable = false;
    this.lastRollTime = currentTime;
    this.onRollEnd();
  }

  /**
   * Checks if the player is currently invulnerable
   * @returns {boolean}
   */
  getIsInvulnerable() {
    return this.isInvulnerable;
  }

  /**
   * Checks if the player is currently rolling
   * @returns {boolean}
   */
  getIsRolling() {
    return this.isRolling;
  }

  /**
   * Gets the time remaining until the next roll can be performed
   * @param {number} currentTime - Current game time in seconds
   * @returns {number} - Time remaining in seconds (0 if ready)
   */
  getCooldownRemaining(currentTime = Date.now() / 1000) {
    const timeSinceLastRoll = currentTime - this.lastRollTime;
    return Math.max(0, this.rollCooldown - timeSinceLastRoll);
  }

  /**
   * Checks if a roll can be performed
   * @param {number} currentTime - Current game time in seconds
   * @returns {boolean}
   */
  canRoll(currentTime = Date.now() / 1000) {
    return !this.isRolling && this.getCooldownRemaining(currentTime) === 0;
  }

  /**
   * Resets the dodge roll state
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