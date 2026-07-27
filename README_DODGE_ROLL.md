# Dodge Roll Mechanic

## Overview

The Dodge Roll mechanic provides a robust, production-ready implementation of a dodge/evasion system for game entities. It includes invulnerability frames, cooldown management, and smooth movement integration.

## Features

- **Directional Rolling**: Roll in any direction with normalized movement
- **Invulnerability Frames (iFrames)**: Configurable invulnerability period during roll
- **Cooldown System**: Prevents spam with configurable cooldown
- **Smooth Movement**: Frame-rate independent movement calculation
- **Event Callbacks**: Hooks for roll start, update, and end events
- **State Management**: Complete state tracking and reset capabilities

## Installation

```javascript
const DodgeRoll = require('./src/mechanics/dodgeRoll');
const DodgeRollController = require('./src/mechanics/dodgeRollController');
```

## Usage

### Basic Setup

```javascript
const entity = {
  position: { x: 100, y: 100 },
  onMove: (position) => console.log('Moved to:', position)
};

const controller = new DodgeRollController(entity, {
  rollDuration: 0.5,      // Duration of roll in seconds
  rollSpeed: 15,          // Units per second
  rollCooldown: 1.0,      // Cooldown between rolls
  iFrames: 0.3            // Invulnerability duration
});
```

### Initiating a Roll

```javascript
const direction = { x: 1, y: 0 }; // Right
const currentTime = Date.now() / 1000;

if (controller.handleDodgeInput(direction, currentTime)) {
  console.log('Roll initiated!');
}
```

### Game Loop Integration

```javascript
function gameLoop(deltaTime, currentTime) {
  // Update dodge roll
  controller.update(deltaTime, currentTime);

  // Check invulnerability for damage calculations
  if (controller.isInvulnerable()) {
    // Skip damage application
  }

  // Check cooldown for UI
  const cooldownRemaining = controller.getCooldownRemaining(currentTime);
  updateCooldownUI(cooldownRemaining);
}
```

## Configuration

### DodgeRoll Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `rollDuration` | number | 0.5 | Duration of roll in seconds |
| `rollSpeed` | number | 15 | Movement speed in units/second |
| `rollCooldown` | number | 1.0 | Cooldown between rolls in seconds |
| `iFrames` | number | 0.3 | Invulnerability frame duration |
| `onRollStart` | function | () => {} | Callback when roll starts |
| `onRollEnd` | function | () => {} | Callback when roll ends |
| `onRollUpdate` | function | () => {} | Callback on each update |

## API Reference

### DodgeRoll

#### `initiateRoll(direction, currentTime)`
Initiates a dodge roll in the specified direction.
- **Parameters**:
  - `direction` (Object): Direction vector {x, y}
  - `currentTime` (number): Current game time in seconds
- **Returns**: boolean - Success status

#### `update(currentTime)`
Updates the dodge roll state.
- **Parameters**:
  - `currentTime` (number): Current game time in seconds
- **Returns**: Object - Movement vector {x, y}

#### `getIsInvulnerable()`
Checks if currently invulnerable.
- **Returns**: boolean

#### `getIsRolling()`
Checks if currently rolling.
- **Returns**: boolean

#### `getCooldownRemaining(currentTime)`
Gets remaining cooldown time.
- **Parameters**:
  - `currentTime` (number): Current game time in seconds
- **Returns**: number - Remaining cooldown in seconds

#### `canRoll(currentTime)`
Checks if a roll can be performed.
- **Parameters**:
  - `currentTime` (number): Current game time in seconds
- **Returns**: boolean

### DodgeRollController

#### `handleDodgeInput(direction, currentTime)`
Handles dodge roll input.
- **Parameters**:
  - `direction` (Object): Direction vector {x, y}
  - `currentTime` (number): Current game time in seconds
- **Returns**: boolean - Success status

#### `update(deltaTime, currentTime)`
Updates dodge roll and applies movement.
- **Parameters**:
  - `deltaTime` (number): Time since last frame in seconds
  - `currentTime` (number): Current game time in seconds

#### `isInvulnerable()`
Gets invulnerability status.
- **Returns**: boolean

#### `isRolling()`
Gets rolling status.
- **Returns**: boolean

#### `setEnabled(enabled)`
Enables/disables dodge rolling.
- **Parameters**:
  - `enabled` (boolean): Enable state

## Testing

Run the test suite:

```bash
npm test -- src/mechanics/__tests__/
```

Tests cover:
- Roll initiation and validation
- Movement calculation
- Invulnerability frame timing
- Cooldown management
- State transitions
- Edge cases and error handling

## Performance Considerations

- **Memory**: Minimal footprint (~2KB per instance)
- **CPU**: O(1) operations per frame
- **Frame-rate Independent**: Uses delta time for smooth movement
- **No Allocations**: Reuses objects to minimize garbage collection

## Error Handling

The implementation includes:
- Direction vector validation
- Null/undefined checks
- State consistency verification
- Graceful degradation when disabled

## Future Enhancements

- Animation state integration
- Particle effect triggers
- Sound effect callbacks
- Network synchronization support
- Customizable easing curves
