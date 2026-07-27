/**
 * Input Handler for Dodge Roll
 * Manages keyboard/controller input for dodge rolling
 */

class DodgeRollInputHandler {
  constructor(config = {}) {
    this.rollKey = config.rollKey || ' '; // Space bar
    this.isPressed = false;
    this.lastPressTime = 0;
    this.doubleTapThreshold = config.doubleTapThreshold || 0.3; // seconds
    this.doubleTapCount = 0;
    this.enableDoubleTap = config.enableDoubleTap !== false;
    this.onRollInput = config.onRollInput || (() => {});
    this.getDirection = config.getDirection || (() => ({ x: 0, y: 0 }));

    this.setupEventListeners();
  }

  /**
   * Setup keyboard event listeners
   */
  setupEventListeners() {
    document.addEventListener('keydown', this.handleKeyDown.bind(this));
    document.addEventListener('keyup', this.handleKeyUp.bind(this));
  }

  /**
   * Handle key down event
   */
  handleKeyDown(event) {
    if (event.code === this.rollKey || event.key === this.rollKey) {
      event.preventDefault();

      if (this.isPressed) {
        return; // Ignore key repeat
      }

      this.isPressed = true;
      const currentTime = Date.now() / 1000;

      // Check for double tap
      if (this.enableDoubleTap) {
        if (currentTime - this.lastPressTime < this.doubleTapThreshold) {
          this.doubleTapCount++;
        } else {
          this.doubleTapCount = 1;
        }
        this.lastPressTime = currentTime;
      }

      // Get current movement direction
      const direction = this.getDirection();

      // Trigger roll input
      this.onRollInput({
        direction,
        isDoubleTap: this.doubleTapCount >= 2,
        timestamp: currentTime
      });
    }
  }

  /**
   * Handle key up event
   */
  handleKeyUp(event) {
    if (event.code === this.rollKey || event.key === this.rollKey) {
      event.preventDefault();
      this.isPressed = false;
    }
  }

  /**
   * Set the direction getter function
   * @param {Function} getter - Function that returns current direction
   */
  setDirectionGetter(getter) {
    if (typeof getter === 'function') {
      this.getDirection = getter;
    }
  }

  /**
   * Cleanup event listeners
   */
  destroy() {
    document.removeEventListener('keydown', this.handleKeyDown.bind(this));
    document.removeEventListener('keyup', this.handleKeyUp.bind(this));
  }
}

module.exports = DodgeRollInputHandler;
