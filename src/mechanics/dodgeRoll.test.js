/**
 * Tests for Dodge Roll Mechanic
 */

const DodgeRoll = require('./dodgeRoll');

describe('DodgeRoll', () => {
  let dodgeRoll;

  beforeEach(() => {
    dodgeRoll = new DodgeRoll({
      rollDuration: 0.5,
      rollSpeed: 10,
      rollCooldown: 1.0,
      iFrames: 0.3
    });
  });

  describe('initialization', () => {
    test('should initialize with default config', () => {
      const roll = new DodgeRoll();
      expect(roll.isRolling).toBe(false);
      expect(roll.isInvulnerable).toBe(false);
      expect(roll.rollDuration).toBe(0.5);
    });

    test('should initialize with custom config', () => {
      expect(dodgeRoll.rollDuration).toBe(0.5);
      expect(dodgeRoll.rollSpeed).toBe(10);
      expect(dodgeRoll.rollCooldown).toBe(1.0);
    });
  });

  describe('attemptRoll', () => {
    test('should successfully initiate a roll with valid direction', () => {
      const result = dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      expect(result).toBe(true);
      expect(dodgeRoll.isRolling).toBe(true);
      expect(dodgeRoll.isInvulnerable).toBe(true);
    });

    test('should normalize direction vector', () => {
      dodgeRoll.attemptRoll({ x: 3, y: 4 }, 0);
      const magnitude = Math.sqrt(
        dodgeRoll.rollDirection.x ** 2 + dodgeRoll.rollDirection.y ** 2
      );
      expect(magnitude).toBeCloseTo(1, 5);
    });

    test('should reject roll if already rolling', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      const result = dodgeRoll.attemptRoll({ x: 0, y: 1 }, 0.1);
      expect(result).toBe(false);
    });

    test('should reject roll if on cooldown', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.isRolling = false; // Simulate roll completion
      const result = dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0.5);
      expect(result).toBe(false);
    });

    test('should allow roll after cooldown expires', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.isRolling = false;
      const result = dodgeRoll.attemptRoll({ x: 1, y: 0 }, 1.1);
      expect(result).toBe(true);
    });

    test('should reject invalid direction', () => {
      const result = dodgeRoll.attemptRoll({ x: 0, y: 0 }, 0);
      expect(result).toBe(false);
    });

    test('should reject null direction', () => {
      const result = dodgeRoll.attemptRoll(null, 0);
      expect(result).toBe(false);
    });
  });

  describe('update', () => {
    test('should return zero movement when not rolling', () => {
      const state = dodgeRoll.update(0);
      expect(state.isRolling).toBe(false);
      expect(state.movement.x).toBe(0);
      expect(state.movement.y).toBe(0);
    });

    test('should calculate movement during roll', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      const state = dodgeRoll.update(0.25);
      expect(state.isRolling).toBe(true);
      expect(state.movement.x).toBeGreaterThan(0);
      expect(state.movement.y).toBe(0);
    });

    test('should complete roll after duration', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      let state = dodgeRoll.update(0.25);
      expect(state.isRolling).toBe(true);
      state = dodgeRoll.update(0.5);
      expect(state.isRolling).toBe(false);
    });

    test('should end invulnerability after iFrames', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      let state = dodgeRoll.update(0.2);
      expect(state.isInvulnerable).toBe(true);
      state = dodgeRoll.update(0.35);
      expect(state.isInvulnerable).toBe(false);
    });

    test('should track progress correctly', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      let state = dodgeRoll.update(0.125);
      expect(state.progress).toBeCloseTo(0.25, 2);
      state = dodgeRoll.update(0.25);
      expect(state.progress).toBeCloseTo(0.5, 2);
    });
  });

  describe('getProgress', () => {
    test('should return 0 when not rolling', () => {
      expect(dodgeRoll.getProgress()).toBe(0);
    });

    test('should return progress between 0 and 1 during roll', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      const progress = dodgeRoll.getProgress();
      expect(progress).toBeGreaterThanOrEqual(0);
      expect(progress).toBeLessThanOrEqual(1);
    });
  });

  describe('getTimeUntilAvailable', () => {
    test('should return 0 when roll is available', () => {
      expect(dodgeRoll.getTimeUntilAvailable()).toBe(0);
    });

    test('should return remaining cooldown time', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.isRolling = false;
      const timeRemaining = dodgeRoll.getTimeUntilAvailable();
      expect(timeRemaining).toBeGreaterThan(0);
      expect(timeRemaining).toBeLessThanOrEqual(1.0);
    });
  });

  describe('isAvailable', () => {
    test('should return true when not rolling and cooldown expired', () => {
      expect(dodgeRoll.isAvailable()).toBe(true);
    });

    test('should return false when rolling', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      expect(dodgeRoll.isAvailable()).toBe(false);
    });
  });

  describe('cancel', () => {
    test('should cancel active roll', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      expect(dodgeRoll.isRolling).toBe(true);
      dodgeRoll.cancel();
      expect(dodgeRoll.isRolling).toBe(false);
      expect(dodgeRoll.isInvulnerable).toBe(false);
    });

    test('should not affect state when not rolling', () => {
      dodgeRoll.cancel();
      expect(dodgeRoll.isRolling).toBe(false);
    });
  });

  describe('reset', () => {
    test('should reset all state', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.reset();
      expect(dodgeRoll.isRolling).toBe(false);
      expect(dodgeRoll.isInvulnerable).toBe(false);
      expect(dodgeRoll.lastRollTime).toBe(0);
      expect(dodgeRoll.rollStartTime).toBe(0);
    });
  });

  describe('callbacks', () => {
    test('should call onRollStart callback', () => {
      const callback = jest.fn();
      const roll = new DodgeRoll({ onRollStart: callback });
      roll.attemptRoll({ x: 1, y: 0 }, 0);
      expect(callback).toHaveBeenCalled();
    });

    test('should call onRollEnd callback', () => {
      const callback = jest.fn();
      const roll = new DodgeRoll({ rollDuration: 0.1, onRollEnd: callback });
      roll.attemptRoll({ x: 1, y: 0 }, 0);
      roll.update(0.1);
      expect(callback).toHaveBeenCalled();
    });

    test('should call onRollUpdate callback', () => {
      const callback = jest.fn();
      const roll = new DodgeRoll({ onRollUpdate: callback });
      roll.attemptRoll({ x: 1, y: 0 }, 0);
      roll.update(0.05);
      expect(callback).toHaveBeenCalled();
    });
  });
});
