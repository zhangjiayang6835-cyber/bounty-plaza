/**
 * Tests for DodgeRollController
 */

const DodgeRollController = require('../dodgeRollController');

describe('DodgeRollController', () => {
  let controller;
  let mockEntity;

  beforeEach(() => {
    mockEntity = {
      position: { x: 0, y: 0 },
      onMove: jest.fn()
    };

    controller = new DodgeRollController(mockEntity, {
      rollDuration: 0.5,
      rollSpeed: 15,
      rollCooldown: 1.0
    });
  });

  describe('handleDodgeInput', () => {
    it('should initiate roll with valid input', () => {
      const result = controller.handleDodgeInput({ x: 1, y: 0 }, 0);
      expect(result).toBe(true);
      expect(controller.isRolling()).toBe(true);
    });

    it('should not initiate roll when disabled', () => {
      controller.setEnabled(false);
      const result = controller.handleDodgeInput({ x: 1, y: 0 }, 0);
      expect(result).toBe(false);
    });
  });

  describe('update', () => {
    it('should apply movement to entity during roll', () => {
      controller.handleDodgeInput({ x: 1, y: 0 }, 0);
      controller.update(0.016, 0.016); // ~60 FPS
      expect(mockEntity.position.x).not.toBe(0);
    });

    it('should not update when disabled', () => {
      controller.handleDodgeInput({ x: 1, y: 0 }, 0);
      controller.setEnabled(false);
      const initialX = mockEntity.position.x;
      controller.update(0.016, 0.016);
      expect(mockEntity.position.x).toBe(initialX);
    });
  });

  describe('isInvulnerable', () => {
    it('should return true during iFrames', () => {
      controller.handleDodgeInput({ x: 1, y: 0 }, 0);
      expect(controller.isInvulnerable()).toBe(true);
    });
  });

  describe('setEnabled', () => {
    it('should end roll when disabled during roll', () => {
      controller.handleDodgeInput({ x: 1, y: 0 }, 0);
      controller.setEnabled(false);
      expect(controller.isRolling()).toBe(false);
    });
  });

  describe('reset', () => {
    it('should reset controller state', () => {
      controller.handleDodgeInput({ x: 1, y: 0 }, 0);
      controller.reset();
      expect(controller.isRolling()).toBe(false);
    });
  });
});
