const DodgeRoll = require('./dodgeRoll');

describe('DodgeRoll', () => {
  let dodgeRoll;

  beforeEach(() => {
    dodgeRoll = new DodgeRoll({
      duration: 0.5,
      cooldown: 1.0,
      distance: 10,
      invulnerabilityFrames: 0.3
    });
  });

  describe('initialization', () => {
    test('should initialize with default values', () => {
      const dodge = new DodgeRoll();
      expect(dodge.duration).toBe(0.5);
      expect(dodge.cooldown).toBe(1.0);
      expect(dodge.distance).toBe(10);
      expect(dodge.isActive).toBe(false);
    });

    test('should initialize with custom values', () => {
      const dodge = new DodgeRoll({
        duration: 0.3,
        cooldown: 0.8,
        distance: 15
      });
      expect(dodge.duration).toBe(0.3);
      expect(dodge.cooldown).toBe(0.8);
      expect(dodge.distance).toBe(15);
    });
  });

  describe('canDodge', () => {
    test('should return true when dodge is available', () => {
      expect(dodgeRoll.canDodge()).toBe(true);
    });

    test('should return false when dodge is active', () => {
      dodgeRoll.initiate({ x: 1, y: 0 });
      expect(dodgeRoll.canDodge()).toBe(false);
    });
  });

  describe('initiate', () => {
    test('should initiate dodge with direction', () => {
      const result = dodgeRoll.initiate({ x: 1, y: 0 });
      expect(result).toBe(true);
      expect(dodgeRoll.isActive).toBe(true);
    });

    test('should normalize direction vector', () => {
      dodgeRoll.initiate({ x: 2, y: 0 });
      expect(dodgeRoll.direction.x).toBeCloseTo(1, 5);
      expect(dodgeRoll.direction.y).toBeCloseTo(0, 5);
    });

    test('should calculate correct velocity', () => {
      dodgeRoll.initiate({ x: 1, y: 0 });
      const expectedSpeed = dodgeRoll.distance / dodgeRoll.duration;
      expect(dodgeRoll.currentVelocity.x).toBeCloseTo(expectedSpeed, 5);
    });

    test('should fail if dodge is on cooldown', () => {
      dodgeRoll.initiate({ x: 1, y: 0 });
      dodgeRoll.isActive = false;
      dodgeRoll.lastDodgeTime = Date.now() / 1000;
      const result = dodgeRoll.initiate({ x: 1, y: 0 });
      expect(result).toBe(false);
    });

    test('should use default direction if none provided', () => {
      dodgeRoll.initiate();
      expect(dodgeRoll.direction.x).toBe(0);
      expect(dodgeRoll.direction.y).toBe(1);
    });
  });

  describe('update', () => {
    test('should return zero velocity when inactive', () => {
      const state = dodgeRoll.update(0.016);
      expect(state.velocity.x).toBe(0);
      expect(state.velocity.y).toBe(0);
      expect(state.isActive).toBe(false);
    });

    test('should return velocity during active dodge', () => {
      dodgeRoll.initiate({ x: 1, y: 0 });
      const state = dodgeRoll.update(0.016);
      expect(state.isActive).toBe(true);
      expect(state.velocity.x).toBeGreaterThan(0);
    });

    test('should mark as invulnerable during invulnerability frames', () => {
      dodgeRoll.initiate({ x: 1, y: 0 });
      const state = dodgeRoll.update(0.016);
      expect(state.isInvulnerable).toBe(true);
    });

    test('should deactivate after duration', (done) => {
      dodgeRoll.initiate({ x: 1, y: 0 });
      setTimeout(() => {
        const state = dodgeRoll.update(0.016);
        expect(state.isActive).toBe(false);
        done();
      }, 600);
    });
  });

  describe('getRemainingCooldown', () => {
    test('should return 0 when dodge is available', () => {
      expect(dodgeRoll.getRemainingCooldown()).toBe(0);
    });

    test('should return remaining cooldown after dodge', () => {
      dodgeRoll.initiate({ x: 1, y: 0 });
      dodgeRoll.isActive = false;
      const remaining = dodgeRoll.getRemainingCooldown();
      expect(remaining).toBeGreaterThan(0);
      expect(remaining).toBeLessThanOrEqual(dodgeRoll.cooldown);
    });
  });

  describe('isInvulnerable', () => {
    test('should return false when inactive', () => {
      expect(dodgeRoll.isInvulnerable()).toBe(false);
    });

    test('should return true during invulnerability frames', () => {
      dodgeRoll.initiate({ x: 1, y: 0 });
      expect(dodgeRoll.isInvulnerable()).toBe(true);
    });
  });

  describe('cancel', () => {
    test('should cancel active dodge', () => {
      dodgeRoll.initiate({ x: 1, y: 0 });
      dodgeRoll.cancel();
      expect(dodgeRoll.isActive).toBe(false);
      expect(dodgeRoll.currentVelocity.x).toBe(0);
      expect(dodgeRoll.currentVelocity.y).toBe(0);
    });
  });

  describe('reset', () => {
    test('should reset to initial state', () => {
      dodgeRoll.initiate({ x: 1, y: 0 });
      dodgeRoll.reset();
      expect(dodgeRoll.isActive).toBe(false);
      expect(dodgeRoll.lastDodgeTime).toBe(0);
      expect(dodgeRoll.currentVelocity.x).toBe(0);
      expect(dodgeRoll.currentVelocity.y).toBe(0);
    });
  });
});
