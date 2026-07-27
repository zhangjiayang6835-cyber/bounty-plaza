/**
 * Tests for DodgeRoll mechanic
 */

const DodgeRoll = require('../dodgeRoll');

describe('DodgeRoll', () => {
  let dodgeRoll;
  let mockCallbacks;

  beforeEach(() => {
    mockCallbacks = {
      onRollStart: jest.fn(),
      onRollEnd: jest.fn(),
      onRollUpdate: jest.fn()
    };

    dodgeRoll = new DodgeRoll({
      rollDuration: 0.5,
      rollSpeed: 15,
      rollCooldown: 1.0,
      iFrames: 0.3,
      ...mockCallbacks
    });
  });

  describe('initiateRoll', () => {
    it('should successfully initiate a roll with valid direction', () => {
      const result = dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      expect(result).toBe(true);
      expect(dodgeRoll.isRolling).toBe(true);
      expect(mockCallbacks.onRollStart).toHaveBeenCalled();
    });

    it('should fail to initiate roll when already rolling', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      const result = dodgeRoll.initiateRoll({ x: 0, y: 1 }, 0.1);
      expect(result).toBe(false);
    });

    it('should fail to initiate roll during cooldown', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.endRoll(0.5);
      const result = dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0.7);
      expect(result).toBe(false);
    });

    it('should fail with zero direction vector', () => {
      const result = dodgeRoll.initiateRoll({ x: 0, y: 0 }, 0);
      expect(result).toBe(false);
    });

    it('should normalize direction vector', () => {
      dodgeRoll.initiateRoll({ x: 3, y: 4 }, 0);
      const magnitude = Math.sqrt(
        dodgeRoll.rollDirection.x ** 2 + dodgeRoll.rollDirection.y ** 2
      );
      expect(magnitude).toBeCloseTo(1.0, 5);
    });
  });

  describe('update', () => {
    it('should return zero movement when not rolling', () => {
      const movement = dodgeRoll.update(0);
      expect(movement.x).toBe(0);
      expect(movement.y).toBe(0);
    });

    it('should return movement during roll', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      const movement = dodgeRoll.update(0.1);
      expect(movement.x).not.toBe(0);
    });

    it('should end roll after duration expires', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.update(0.6);
      expect(dodgeRoll.isRolling).toBe(false);
    });

    it('should grant invulnerability during iFrames', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      expect(dodgeRoll.isInvulnerable).toBe(true);
      dodgeRoll.update(0.2);
      expect(dodgeRoll.isInvulnerable).toBe(true);
    });

    it('should remove invulnerability after iFrames expire', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.update(0.35);
      expect(dodgeRoll.isInvulnerable).toBe(false);
    });
  });

  describe('endRoll', () => {
    it('should end the roll and trigger callback', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.endRoll(0.5);
      expect(dodgeRoll.isRolling).toBe(false);
      expect(mockCallbacks.onRollEnd).toHaveBeenCalled();
    });

    it('should remove invulnerability when ending roll', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.endRoll(0.5);
      expect(dodgeRoll.isInvulnerable).toBe(false);
    });
  });

  describe('getCooldownRemaining', () => {
    it('should return 0 when cooldown is complete', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.endRoll(0.5);
      const remaining = dodgeRoll.getCooldownRemaining(1.5);
      expect(remaining).toBe(0);
    });

    it('should return remaining cooldown time', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.endRoll(0.5);
      const remaining = dodgeRoll.getCooldownRemaining(1.0);
      expect(remaining).toBeCloseTo(0.5, 1);
    });
  });

  describe('canRoll', () => {
    it('should return false when already rolling', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      expect(dodgeRoll.canRoll(0.1)).toBe(false);
    });

    it('should return false during cooldown', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.endRoll(0.5);
      expect(dodgeRoll.canRoll(0.7)).toBe(false);
    });

    it('should return true when ready to roll', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.endRoll(0.5);
      expect(dodgeRoll.canRoll(1.5)).toBe(true);
    });
  });

  describe('reset', () => {
    it('should reset all state', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, 0);
      dodgeRoll.reset();
      expect(dodgeRoll.isRolling).toBe(false);
      expect(dodgeRoll.isInvulnerable).toBe(false);
      expect(dodgeRoll.lastRollTime).toBe(0);
    });
  });
});
