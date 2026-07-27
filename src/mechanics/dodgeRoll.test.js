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
    test('should initialize with default values', () => {
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

    test('should fail if already rolling', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      const result = dodgeRoll.attemptRoll({ x: 0, y: 1 }, 0.1);
      expect(result).toBe(false);
    });

    test('should fail if on cooldown', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.isRolling = false; // Simulate roll completion
      const result = dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0.5);
      expect(result).toBe(false);
    });

    test('should fail with zero direction', () => {
      const result = dodgeRoll.attemptRoll({ x: 0, y: 0 }, 0);
      expect(result).toBe(false);
    });

    test('should normalize direction vector', () => {
      dodgeRoll.attemptRoll({ x: 3, y: 4 }, 0);
      const length = Math.sqrt(
        dodgeRoll.rollDirection.x ** 2 + dodgeRoll.rollDirection.y ** 2
      );
      expect(Math.abs(length - 1)).toBeLessThan(0.0001);
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
      expect(state.progress).toBeLessThan(1);
    });

    test('should complete roll after duration', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      const state = dodgeRoll.update(0.6);
      expect(state.isRolling).toBe(false);
      expect(state.progress).toBe(1);
    });

    test('should grant invulnerability during iFrames', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      let state = dodgeRoll.update(0.1);
      expect(state.isInvulnerable).toBe(true);

      state = dodgeRoll.update(0.35);
      expect(state.isInvulnerable).toBe(false);
    });
  });

  describe('getState', () => {
    test('should return current state', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      const state = dodgeRoll.getState();
      expect(state.isRolling).toBe(true);
      expect(state.isInvulnerable).toBe(true);
      expect(state.rollDirection.x).toBeCloseTo(1);
    });
  });

  describe('cancel', () => {
    test('should cancel active roll', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.cancel();
      expect(dodgeRoll.isRolling).toBe(false);
      expect(dodgeRoll.isInvulnerable).toBe(false);
    });

    test('should not affect non-rolling state', () => {
      dodgeRoll.cancel();
      expect(dodgeRoll.isRolling).toBe(false);
    });
  });

  describe('cooldown', () => {
    test('should track cooldown correctly', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.isRolling = false;

      let remaining = dodgeRoll.getCooldownRemaining(0.5);
      expect(remaining).toBeGreaterThan(0);

      remaining = dodgeRoll.getCooldownRemaining(1.1);
      expect(remaining).toBe(0);
    });

    test('should report availability correctly', () => {
      expect(dodgeRoll.isAvailable(0)).toBe(true);

      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      expect(dodgeRoll.isAvailable(0.1)).toBe(false);

      dodgeRoll.isRolling = false;
      expect(dodgeRoll.isAvailable(0.5)).toBe(false);
      expect(dodgeRoll.isAvailable(1.1)).toBe(true);
    });
  });

  describe('reset', () => {
    test('should reset all state', () => {
      dodgeRoll.attemptRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.reset();
      expect(dodgeRoll.isRolling).toBe(false);
      expect(dodgeRoll.isInvulnerable).toBe(false);
      expect(dodgeRoll.lastRollTime).toBe(0);
    });
  });
});
