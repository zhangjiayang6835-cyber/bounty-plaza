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
      rollCooldown: 1.0
    });
  });

  describe('initiateRoll', () => {
    it('should successfully initiate a roll with valid direction', () => {
      const result = dodgeRoll.initiateRoll(
        { x: 1, y: 0 },
        { x: 0, y: 0 }
      );
      expect(result).toBe(true);
      expect(dodgeRoll.isRolling).toBe(true);
    });

    it('should normalize direction vector', () => {
      dodgeRoll.initiateRoll(
        { x: 3, y: 4 },
        { x: 0, y: 0 }
      );
      const magnitude = Math.sqrt(
        dodgeRoll.rollDirection.x ** 2 + dodgeRoll.rollDirection.y ** 2
      );
      expect(Math.abs(magnitude - 1)).toBeLessThan(0.0001);
    });

    it('should reject roll with zero direction', () => {
      const result = dodgeRoll.initiateRoll(
        { x: 0, y: 0 },
        { x: 0, y: 0 }
      );
      expect(result).toBe(false);
      expect(dodgeRoll.isRolling).toBe(false);
    });

    it('should reject roll while already rolling', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, { x: 0, y: 0 });
      const result = dodgeRoll.initiateRoll(
        { x: 0, y: 1 },
        { x: 0, y: 0 }
      );
      expect(result).toBe(false);
    });

    it('should reject roll during cooldown', (done) => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, { x: 0, y: 0 });
      dodgeRoll.cancelRoll();

      const result = dodgeRoll.initiateRoll(
        { x: 1, y: 0 },
        { x: 0, y: 0 }
      );
      expect(result).toBe(false);

      setTimeout(() => {
        const result2 = dodgeRoll.initiateRoll(
          { x: 1, y: 0 },
          { x: 0, y: 0 }
        );
        expect(result2).toBe(true);
        done();
      }, 1100);
    });

    it('should reject invalid direction input', () => {
      const result = dodgeRoll.initiateRoll(null, { x: 0, y: 0 });
      expect(result).toBe(false);
    });
  });

  describe('update', () => {
    it('should return current position when not rolling', () => {
      const position = { x: 5, y: 5 };
      const result = dodgeRoll.update(position);
      expect(result.x).toBe(5);
      expect(result.y).toBe(5);
      expect(result.isRolling).toBe(false);
    });

    it('should move position during roll', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, { x: 0, y: 0 });
      const result = dodgeRoll.update({ x: 0, y: 0 });
      expect(result.x).toBeGreaterThan(0);
      expect(result.isRolling).toBe(true);
    });

    it('should complete roll after duration', (done) => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, { x: 0, y: 0 });
      
      setTimeout(() => {
        const result = dodgeRoll.update({ x: 0, y: 0 });
        expect(result.isRolling).toBe(false);
        expect(result.progress).toBe(1);
        done();
      }, 600);
    });

    it('should track progress correctly', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, { x: 0, y: 0 });
      const result = dodgeRoll.update({ x: 0, y: 0 });
      expect(result.progress).toBeGreaterThan(0);
      expect(result.progress).toBeLessThanOrEqual(1);
    });
  });

  describe('cancelRoll', () => {
    it('should cancel active roll', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, { x: 0, y: 0 });
      const result = dodgeRoll.cancelRoll();
      expect(result).toBe(true);
      expect(dodgeRoll.isRolling).toBe(false);
    });

    it('should return false when no roll is active', () => {
      const result = dodgeRoll.cancelRoll();
      expect(result).toBe(false);
    });
  });

  describe('getState', () => {
    it('should return current state', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, { x: 0, y: 0 });
      const state = dodgeRoll.getState();
      expect(state.isRolling).toBe(true);
      expect(state.cooldownRemaining).toBe(0);
      expect(state.rollDirection).toBeDefined();
    });

    it('should show cooldown remaining', (done) => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, { x: 0, y: 0 });
      dodgeRoll.cancelRoll();
      
      const state = dodgeRoll.getState();
      expect(state.cooldownRemaining).toBeGreaterThan(0);
      expect(state.cooldownRemaining).toBeLessThanOrEqual(1.0);
      done();
    });
  });

  describe('reset', () => {
    it('should reset all state', () => {
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, { x: 0, y: 0 });
      dodgeRoll.reset();
      expect(dodgeRoll.isRolling).toBe(false);
      expect(dodgeRoll.rollDirection.x).toBe(0);
      expect(dodgeRoll.rollDirection.y).toBe(0);
    });
  });

  describe('callbacks', () => {
    it('should call onRollStart callback', () => {
      const callback = jest.fn();
      dodgeRoll.onRollStart = callback;
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, { x: 0, y: 0 });
      expect(callback).toHaveBeenCalled();
    });

    it('should call onRollUpdate callback', () => {
      const callback = jest.fn();
      dodgeRoll.onRollUpdate = callback;
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, { x: 0, y: 0 });
      dodgeRoll.update({ x: 0, y: 0 });
      expect(callback).toHaveBeenCalled();
    });

    it('should call onRollEnd callback', (done) => {
      const callback = jest.fn();
      dodgeRoll.onRollEnd = callback;
      dodgeRoll.initiateRoll({ x: 1, y: 0 }, { x: 0, y: 0 });
      
      setTimeout(() => {
        dodgeRoll.update({ x: 0, y: 0 });
        expect(callback).toHaveBeenCalled();
        done();
      }, 600);
    });
  });
});
