class DodgeRoll {
  constructor(config = {}) {
    this.duration = config.duration || 0.5; // seconds
    this.cooldown = config.cooldown || 1.0; // seconds
    this.distance = config.distance || 10; // units
    this.invulnerabilityFrames = config.invulnerabilityFrames || 0.3; // seconds
    this.isActive = false;
    this.lastDodgeTime = 0;
    this.currentVelocity = { x: 0, y: 0 };
    this.startTime = 0;
    this.direction = { x: 0, y: 1 }; // default direction
  }

  /**
   * Check if dodge roll can be performed
   * @returns {boolean} True if dodge is available
   */
  canDodge() {
    const timeSinceLastDodge = Date.now() / 1000 - this.lastDodgeTime;
    return !this.isActive && timeSinceLastDodge >= this.cooldown;
  }

  /**
   * Initiate a dodge roll in the specified direction
   * @param {Object} direction - Direction vector {x, y}
   * @returns {boolean} True if dodge was initiated successfully
   */
  initiate(direction = null) {
    if (!this.canDodge()) {
      return false;
    }

    if (!direction) {
      direction = { x: 0, y: 1 };
    }

    // Normalize direction vector
    const magnitude = Math.sqrt(direction.x ** 2 + direction.y ** 2);
    if (magnitude > 0) {
      this.direction = {
        x: direction.x / magnitude,
        y: direction.y / magnitude
      };
    }

    this.isActive = true;
    this.startTime = Date.now() / 1000;
    this.lastDodgeTime = this.startTime;

    // Calculate velocity based on distance and duration
    const speed = this.distance / this.duration;
    this.currentVelocity = {
      x: this.direction.x * speed,
      y: this.direction.y * speed
    };

    return true;
  }

  /**
   * Update dodge roll state
   * @param {number} deltaTime - Time elapsed since last update in seconds
   * @returns {Object} Current velocity and state
   */
  update(deltaTime) {
    if (!this.isActive) {
      return {
        velocity: { x: 0, y: 0 },
        isActive: false,
        isInvulnerable: false
      };
    }

    const elapsedTime = Date.now() / 1000 - this.startTime;
    const progress = elapsedTime / this.duration;

    if (progress >= 1) {
      this.isActive = false;
      this.currentVelocity = { x: 0, y: 0 };
      return {
        velocity: { x: 0, y: 0 },
        isActive: false,
        isInvulnerable: false
      };
    }

    const isInvulnerable = elapsedTime < this.invulnerabilityFrames;

    return {
      velocity: this.currentVelocity,
      isActive: true,
      isInvulnerable: isInvulnerable,
      progress: progress
    };
  }

  /**
   * Get remaining cooldown time
   * @returns {number} Remaining cooldown in seconds
   */
  getRemainingCooldown() {
    const timeSinceLastDodge = Date.now() / 1000 - this.lastDodgeTime;
    const remaining = this.cooldown - timeSinceLastDodge;
    return Math.max(0, remaining);
  }

  /**
   * Check if currently invulnerable
   * @returns {boolean} True if in invulnerability frames
   */
  isInvulnerable() {
    if (!this.isActive) return false;
    const elapsedTime = Date.now() / 1000 - this.startTime;
    return elapsedTime < this.invulnerabilityFrames;
  }

  /**
   * Cancel active dodge roll
   */
  cancel() {
    this.isActive = false;
    this.currentVelocity = { x: 0, y: 0 };
  }

  /**
   * Reset dodge roll to initial state
   */
  reset() {
    this.isActive = false;
    this.lastDodgeTime = 0;
    this.currentVelocity = { x: 0, y: 0 };
    this.startTime = 0;
    this.direction = { x: 0, y: 1 };
  }
}

module.exports = DodgeRoll;