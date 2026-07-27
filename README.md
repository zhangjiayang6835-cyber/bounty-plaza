# Dodge Rolling Mechanic

A production-ready implementation of a dodge rolling system for game mechanics.

## Features

- **Smooth Dodge Rolling**: Implements directional dodge rolls with configurable duration and speed
- **Cooldown System**: Prevents spam with configurable cooldown periods
- **Invulnerability Frames**: Optional invulnerability during dodge rolls
- **Animation Integration**: Hooks for animation state management
- **Event Callbacks**: Comprehensive callback system for roll events
- **Fully Tested**: Complete test coverage with Jest

## Installation

```bash
npm install
```

## Usage

### Basic Dodge Roll

```javascript
const DodgeRoll = require('./src/mechanics/dodgeRoll');

const dodgeRoll = new DodgeRoll({
  rollDuration: 0.5,      // Duration in seconds
  rollSpeed: 15,          // Units per second
  rollCooldown: 1.0       // Cooldown in seconds
});

// Initiate a roll
const success = dodgeRoll.initiateRoll(
  { x: 1, y: 0 },        // Direction
  { x: 0, y: 0 }         // Current position
);

// Update each frame
const newPosition = dodgeRoll.update({ x: 0, y: 0 });
```

### Player Integration

```javascript
const PlayerDodgeRoll = require('./src/integration/playerDodgeRoll');

const playerDodgeRoll = new PlayerDodgeRoll(player, {
  rollDuration: 0.5,
  rollSpeed: 15,
  rollCooldown: 1.0,
  invulnerabilityDuration: 0.3
});

// Perform dodge roll
playerDodgeRoll.performDodgeRoll({ x: 1, y: 0 });

// Update each frame
playerDodgeRoll.update();
```

## Configuration

### DodgeRoll Options

- `rollDuration` (number): How long the roll lasts in seconds (default: 0.5)
- `rollSpeed` (number): How fast the character moves during roll in units/second (default: 15)
- `rollCooldown` (number): Time between rolls in seconds (default: 1.0)
- `onRollStart` (function): Callback when roll starts
- `onRollUpdate` (function): Callback when roll updates
- `onRollEnd` (function): Callback when roll ends

### PlayerDodgeRoll Options

All DodgeRoll options plus:

- `invulnerabilityDuration` (number): How long invulnerability lasts in seconds (default: 0.3)

## API

### DodgeRoll

#### `initiateRoll(direction, currentPosition)`
Initiates a dodge roll in the specified direction.

**Parameters:**
- `direction` (Object): Direction vector {x, y}
- `currentPosition` (Object): Current position {x, y}

**Returns:** boolean - Success status

#### `update(currentPosition)`
Updates the dodge roll state and returns new position.

**Parameters:**
- `currentPosition` (Object): Current position {x, y}

**Returns:** Object - {x, y, isRolling, progress}

#### `cancelRoll()`
Cancels the current dodge roll.

**Returns:** boolean - Whether a roll was cancelled

#### `getState()`
Gets the current roll state.

**Returns:** Object - State information

#### `reset()`
Resets the dodge roll system.

### PlayerDodgeRoll

#### `performDodgeRoll(direction)`
Attempts to perform a dodge roll.

**Parameters:**
- `direction` (Object): Direction to roll {x, y}

**Returns:** boolean - Success status

#### `update()`
Updates the player's dodge roll state. Call every frame.

#### `getState()`
Gets the current state including invulnerability and animation state.

**Returns:** Object - State information

#### `cancelDodgeRoll()`
Cancels the current dodge roll.

**Returns:** boolean - Success status

#### `reset()`
Resets the dodge roll system.

## Testing

```bash
npm test
```

Run tests with coverage:

```bash
npm test -- --coverage
```

## Error Handling

The implementation includes comprehensive error handling:

- Validates direction vectors (non-zero magnitude)
- Checks for null/undefined inputs
- Prevents rolling while already rolling
- Enforces cooldown periods
- Validates player object in PlayerDodgeRoll

## Performance Considerations

- Lightweight calculations suitable for 60+ FPS
- No external dependencies
- Efficient state management
- Minimal memory footprint

## License

MIT
