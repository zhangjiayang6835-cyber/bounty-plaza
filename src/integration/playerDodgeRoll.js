/**
 * Player Dodge Roll Integration
 * Integrates dodge rolling into player character mechanics
 */

const DodgeRoll = require('../mechanics/dodgeRoll');

class PlayerDodgeRoll {
  constructor(player, config = {}) {
    if (!player) {
      throw new Error('Player object is required');
    }

    this.player = player;
    this.dodgeRoll = new DodgeRoll({
      rollDuration: config.rollDuration || 0.5,
      rollSpeed: config.rollSpeed || 15,
      rollCooldown: config.rollCooldown || 1.0,
      onRollStart: this.onRollStart.bind(this),
      onRollUpdate: this.onRollUpdate.bind(this),
      onRollEnd: this.onRollEnd.bind(this)
    });

    this.isInvulnerable = false;
    this.invulnerabilityDuration = config.invulnerabilityDuration || 0.3;
    this.invulnerabilityStartTime = 0;
    this.animationState = 'idle';
  }

  /**
   * Attempts to perform a dodge roll
   * @param {Object} direction - Direction to roll {x, y}
   * @returns {boolean} - Whether the roll was initiated
   */
  performDodgeRoll(direction) {
    if (!this.player.position) {
      console.error('Player position is not defined');
      return false;
    }

    return this.dodgeRoll.initiateRoll(direction, this.player.position);
  }

  /**
   * Updates the player's dodge roll state
   * Should be called every frame
   */
  update() {
    const updatedPosition = this.dodgeRoll.update(this.player.position);
    
    if (updatedPosition.isRolling) {
      this.player.position = {
        x: updatedPosition.x,
        y: updatedPosition.y
      };
    }

    // Update invulnerability state
    if (this.isInvulnerable) {
      const currentTime = Date.now() / 1000;
      if (currentTime - this.invulnerabilityStartTime > this.invulnerabilityDuration) {
        this.isInvulnerable = false;
        this.player.setInvulnerable(false);
      }
    }
  }

  /**
   * Callback when roll starts
   * @private
   */
  onRollStart(data) {
    this.animationState = 'rolling';
    this.isInvulnerable = true;
    this.invulnerabilityStartTime = Date.now() / 1000;
    
    if (this.player.setInvulnerable) {
      this.player.setInvulnerable(true);
    }

    if (this.player.playAnimation) {
      this.player.playAnimation('dodge_roll', {
        direction: data.direction
      });
    }

    if (this.player.onDodgeRollStart) {
      this.player.onDodgeRollStart(data);
    }
  }

  /**
   * Callback when roll updates
   * @private
   */
  onRollUpdate(data) {
    if (this.player.onDodgeRollUpdate) {
      this.player.onDodgeRollUpdate(data);
    }
  }

  /**
   * Callback when roll ends
   * @private
   */
  onRollEnd(data) {
    this.animationState = 'idle';
    
    if (this.player.playAnimation) {
      this.player.playAnimation('idle');
    }

    if (this.player.onDodgeRollEnd) {
      this.player.onDodgeRollEnd(data);
    }
  }

  /**
   * Gets the current dodge roll state
   * @returns {Object} - State information
   */
  getState() {
    return {
      ...this.dodgeRoll.getState(),
      isInvulnerable: this.isInvulnerable,
      animationState: this.animationState
    };
  }

  /**
   * Cancels the current dodge roll
   * @returns {boolean} - Whether a roll was cancelled
   */
  cancelDodgeRoll() {
    return this.dodgeRoll.cancelRoll();
  }

  /**
   * Resets the dodge roll system
   */
  reset() {
    this.dodgeRoll.reset();
    this.isInvulnerable = false;
    this.animationState = 'idle';
  }
}

module.exports = PlayerDodgeRoll;
