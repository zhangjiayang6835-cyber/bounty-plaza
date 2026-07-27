/**
 * Tests for Player Dodge Roll Integration
 */

const PlayerDodgeRoll = require('./playerDodgeRoll');

describe('PlayerDodgeRoll', () => {
  let playerDodgeRoll;
  let mockPlayer;

  beforeEach(() => {
    mockPlayer = {
      position: { x: 0, y: 0 },
      setInvulnerable: jest.fn(),
      playAnimation: jest.fn(),
      onDodgeRollStart: jest.fn(),
      onDodgeRollUpdate: jest.fn(),
      onDodgeRollEnd: jest.fn()
    };

    playerDodgeRoll = new PlayerDodgeRoll(mockPlayer, {
      rollDuration: 0.5,
      rollSpeed: 10,
      rollCooldown: 1.0,
      invulnerabilityDuration: 0.3
    });
  });

  describe('constructor', () => {
    it('should throw error if player is not provided', () => {
      expect(() => new PlayerDodgeRoll(null)).toThrow();
    });

    it('should initialize with default config', () => {
      const player = { position: { x: 0, y: 0 } };
      const pdr = new PlayerDodgeRoll(player);
      expect(pdr.player).toBe(player);
      expect(pdr.dodgeRoll).toBeDefined();
    });
  });

  describe('performDodgeRoll', () => {
    it('should initiate dodge roll with valid direction', () => {
      const result = playerDodgeRoll.performDodgeRoll({ x: 1, y: 0 });
      expect(result).toBe(true);
    });

    it('should return false if player position is not defined', () => {
      mockPlayer.position = null;
      const result = playerDodgeRoll.performDodgeRoll({ x: 1, y: 0 });
      expect(result).toBe(false);
    });

    it('should call onRollStart callback', () => {
      playerDodgeRoll.performDodgeRoll({ x: 1, y: 0 });
      expect(mockPlayer.onDodgeRollStart).toHaveBeenCalled();
    });
  });

  describe('update', () => {
    it('should update player position during roll', () => {
      playerDodgeRoll.performDodgeRoll({ x: 1, y: 0 });
      const initialX = mockPlayer.position.x;
      playerDodgeRoll.update();
      expect(mockPlayer.position.x).toBeGreaterThan(initialX);
    });

    it('should set invulnerability during roll', () => {
      playerDodgeRoll.performDodgeRoll({ x: 1, y: 0 });
      expect(playerDodgeRoll.isInvulnerable).toBe(true);
      expect(mockPlayer.setInvulnerable).toHaveBeenCalledWith(true);
    });

    it('should remove invulnerability after duration', (done) => {
      playerDodgeRoll.performDodgeRoll({ x: 1, y: 0 });
      expect(playerDodgeRoll.isInvulnerable).toBe(true);

      setTimeout(() => {
        playerDodgeRoll.update();
        expect(playerDodgeRoll.isInvulnerable).toBe(false);
        expect(mockPlayer.setInvulnerable).toHaveBeenCalledWith(false);
        done();
      }, 350);
    });
  });

  describe('getState', () => {
    it('should return current state', () => {
      playerDodgeRoll.performDodgeRoll({ x: 1, y: 0 });
      const state = playerDodgeRoll.getState();
      expect(state.isRolling).toBe(true);
      expect(state.isInvulnerable).toBe(true);
      expect(state.animationState).toBe('rolling');
    });
  });

  describe('cancelDodgeRoll', () => {
    it('should cancel active roll', () => {
      playerDodgeRoll.performDodgeRoll({ x: 1, y: 0 });
      const result = playerDodgeRoll.cancelDodgeRoll();
      expect(result).toBe(true);
    });
  });

  describe('reset', () => {
    it('should reset all state', () => {
      playerDodgeRoll.performDodgeRoll({ x: 1, y: 0 });
      playerDodgeRoll.reset();
      expect(playerDodgeRoll.isInvulnerable).toBe(false);
      expect(playerDodgeRoll.animationState).toBe('idle');
    });
  });
});
