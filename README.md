# Dodge Roll System

A production-ready dodge rolling mechanic implementation for game development.

## Features

- **Smooth Animation**: Ease-out cubic easing for natural movement
- **Invulnerability Frames**: Configurable i-frames during dodge
- **Cooldown System**: Prevents spam with customizable cooldown
- **Direction Normalization**: Automatic direction vector normalization
- **Event Callbacks**: Hooks for animation, particles, and sound
- **Component Integration**: Easy integration with game entities
- **Full Test Coverage**: Comprehensive unit tests included

## Installation

```bash
npm install dodge-roll-system
```

## Usage

### Basic Usage

```javascript
const { DodgeRoll } = require('dodge-roll-system');

const dodgeRoll = new DodgeRoll({
  rollDuration: 0.5,      // Duration in seconds
  rollSpeed: 15,          // Units per second
  rollCooldown: 1.0,      // Cooldown in seconds
  iFrames: 0.3            // Invulnerability frames
});

// Attempt a dodge roll
const success = dodgeRoll.attemptRoll({ x: 1, y: 0 });

// Update each frame
const state = dodgeRoll.update(currentTime);
console.log(state.movement); // { x: ..., y: ... }
console.log(state.isInvulnerable); // true/false
```

### With Game Entity Component

```javascript
const { DodgeRollComponent } = require('dodge-roll-system');

const component = new DodgeRollComponent(entity, {
  rollDuration: 0.5,
  animationController: myAnimController,
  particleEmitter: myParticleEmitter,
  soundManager: mySoundManager
});

// Perform dodge roll
component.performDodgeRoll({ x: 1, y: 0 });

// Update each frame
component.update(deltaTime);

// Get state
const state = component.getState();
```

## Configuration

### DodgeRoll Options

- `rollDuration` (number): Duration of the dodge roll in seconds (default: 0.5)
- `rollSpeed` (number): Speed of movement during roll in units/second (default: 15)
- `rollCooldown` (number): Cooldown between rolls in seconds (default: 1.0)
- `iFrames` (number): Duration of invulnerability frames in seconds (default: 0.3)
- `onRollStart` (function): Callback when roll starts
- `onRollEnd` (function): Callback when roll ends
- `onRollUpdate` (function): Callback on each update

## API

### DodgeRoll

#### Methods

- `attemptRoll(direction, currentTime)` - Attempt to start a dodge roll
- `update(currentTime)` - Update roll state
- `getState()` - Get current state
- `cancel()` - Cancel active roll
- `reset()` - Reset all state
- `getCooldownRemaining(currentTime)` - Get remaining cooldown
- `isAvailable(currentTime)` - Check if roll is available

### DodgeRollComponent

#### Methods

- `performDodgeRoll(direction)` - Perform a dodge roll
- `update(deltaTime)` - Update component
- `getState()` - Get component state
- `setEnabled(enabled)` - Enable/disable component
- `reset()` - Reset component

## Testing

```bash
npm test
npm run test:coverage
```

## Performance

- Minimal memory allocation
- No external dependencies
- Efficient vector math
- Suitable for mobile and desktop games

## License

MIT
