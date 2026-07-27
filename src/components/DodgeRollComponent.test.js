/**
 * Tests for Dodge Roll Component
 */

const DodgeRollComponent = require('./DodgeRollComponent');

describe('DodgeRollComponent', () => {
  let component;
  let mockEntity;
  let mockAnimationController;
  let mockParticleEmitter;
  let mockSoundManager;

  beforeEach(() => {
    mockEntity = {
      position: { x: 0, y: 0 },
      velocity: { x: 0, y: 0 },
      isDodging: false,
      isInvulnerable: false
    };

    mockAnimationController = {
      play: jest.fn(),
      stop: jest.fn()
    };

    mockParticleEmitter = {
      emit: jest.fn()
    };

    mockSoundManager = {
      play: jest.fn()
    };

    component = new DodgeRollComponent(mockEntity, {
      rollDuration: 0.5,
      rollSpeed: 10,
      rollCooldown: 1.0,
      animationController: mockAnimationController,
      particleEmitter: mockParticleEmitter,
      soundManager: mockSoundManager
    });
  });

  describe('initialization', () => {
    test('should initialize with entity and config', () => {
      expect(component.entity).toBe(mockEntity);
      expect(component.isEnabled).toBe(true);
    });
  });

  describe('performDodgeRoll', () => {
    test('should perform dodge roll with valid direction', () => {
      const result = component.performDodgeRoll({ x: 1, y: 0 });
      expect(result).toBe(true);
      expect(mockEntity.isDodging).toBe(true);
      expect(mockAnimationController.play).toHaveBeenCalled();
      expect(mockSoundManager.play).toHaveBeenCalledWith('dodge_roll', expect.any(Object));
    });

    test('should fail when disabled', () => {
      component.setEnabled(false);
      const result = component.performDodgeRoll({ x: 1, y: 0 });
      expect(result).toBe(false);
    });
  });

  describe('getState', () => {
    test('should return component state', () => {
      component.performDodgeRoll({ x: 1, y: 0 });
      const state = component.getState();
      expect(state.isRolling).toBe(true);
      expect(state.isInvulnerable).toBe(true);
      expect(state.isAvailable).toBe(false);
    });
  });

  describe('setEnabled', () => {
    test('should disable component and cancel roll', () => {
      component.performDodgeRoll({ x: 1, y: 0 });
      component.setEnabled(false);
      expect(component.isEnabled).toBe(false);
      expect(component.dodgeRoll.isRolling).toBe(false);
    });
  });

  describe('reset', () => {
    test('should reset component state', () => {
      component.performDodgeRoll({ x: 1, y: 0 });
      component.reset();
      expect(mockEntity.isDodging).toBe(false);
      expect(mockEntity.isInvulnerable).toBe(false);
    });
  });
});
