# Dodge Roll Implementation

## Overview

This is a production-ready implementation of a dodge roll mechanic for games. It provides a flexible, configurable system for handling player dodge actions with invulnerability frames, cooldowns, and directional movement.

## Features

- **Configurable Duration**: Customize how long the dodge roll lasts
- **Cooldown System**: Prevent spam with configurable cooldown periods
- **Invulnerability Frames**: Grant temporary invulnerability during dodge
- **Directional Movement**: Support for 8-directional or analog stick input
- **State Management**: Track active dodges, cooldowns, and invulnerability
- **UI Integration**: Built-in UI component for displaying dodge status
- **Full Test Coverage**: Comprehensive unit tests included

## Installation

```bash
npm install
```

## Usage

### Basic Setup

```javascript
const DodgeRoll = require('./src/mechanics/dodgeRoll');

const dodgeRoll = new DodgeRoll({
  duration: 0.5,              // How long the dodge lasts (seconds)
  cooldown: 1.0,              // Time before next dodge (seconds)
  distance: 10,               // How far to move (units)
  invulnerabilityFrames: 0.3  // Invulnerability duration (seconds)
});
```

### With Player Controller

```javascript
const PlayerController = require('./src/player/playerController');

const controller = new PlayerController(player, {
  dodgeConfig: {
    duration: 0.5,
    cooldown: 1.0,
    distance: 10,
    invulnerabilityFrames: 0.3
  }
});

// In game loop
controller.update(deltaTime);

// Handle input
controller.handleDodgeInput({ x: 1, y: 0 });
```

### With UI

```javascript
const DodgeRollUI = require('./src/ui/dodgeRollUI');

const ui = new DodgeRollUI({
  containerSelector: '#dodge-ui',
  cooldownBarSelector: '.dodge-cooldown-bar',
  statusTextSelector: '.dodge-status',
  maxCooldown: 1.0
});

// In game loop
ui.update(controller.getDodgeState());
```

## API Reference

### DodgeRoll Class

#### Constructor
```javascript
new DodgeRoll(config)
```

**Config Options:**
- `duration` (number): Dodge duration in seconds (default: 0.5)
- `cooldown` (number): Cooldown between dodges in seconds (default: 1.0)
- `distance` (number): Distance traveled during dodge (default: 10)
- `invulnerabilityFrames` (number): Invulnerability duration in seconds (default: 0.3)

#### Methods

**canDodge(): boolean**
Returns true if a dodge can be performed.

**initiate(direction): boolean**
Initiates a dodge in the specified direction. Returns true if successful.

```javascript
dodgeRoll.initiate({ x: 1, y: 0 }); // Dodge right
```

**update(deltaTime): Object**
Updates the dodge state. Returns:
```javascript
{
  velocity: { x: number, y: number },
  isActive: boolean,
  isInvulnerable: boolean,
  progress: number // 0-1
}
```

**getRemainingCooldown(): number**
Returns remaining cooldown in seconds.

**isInvulnerable(): boolean**
Returns true if currently in invulnerability frames.

**cancel(): void**
Cancels the active dodge.

**reset(): void**
Resets to initial state.

### PlayerController Class

#### Methods

**handleDodgeInput(direction): boolean**
Handles dodge input. Returns true if dodge was initiated.

**update(deltaTime): void**
Updates player state and position.

**getDodgeState(): Object**
Returns current dodge state:
```javascript
{
  isActive: boolean,
  canDodge: boolean,
  remainingCooldown: number,
  isInvulnerable: boolean
}
```

### DodgeRollUI Class

#### Methods

**update(dodgeState): void**
Updates UI based on dodge state.

**showDodgeEffect(): void**
Plays dodge effect animation.

## HTML Setup

```html
<div id="dodge-ui" class="dodge-ui">
  <div class="dodge-status">READY</div>
  <div class="dodge-cooldown-bar-container">
    <div class="dodge-cooldown-bar"></div>
  </div>
</div>
```

## Testing

```bash
npm test
```

Tests cover:
- Initialization
- Dodge availability checks
- Dodge initiation
- State updates
- Cooldown calculations
- Invulnerability frames
- Cancel and reset functionality

## Configuration Examples

### Fast, Short Dodge
```javascript
{
  duration: 0.3,
  cooldown: 0.8,
  distance: 8,
  invulnerabilityFrames: 0.2
}
```

### Slow, Long Dodge
```javascript
{
  duration: 0.8,
  cooldown: 1.5,
  distance: 15,
  invulnerabilityFrames: 0.4
}
```

### High Risk, High Reward
```javascript
{
  duration: 0.4,
  cooldown: 0.5,
  distance: 12,
  invulnerabilityFrames: 0.15
}
```

## Performance Considerations

- Dodge roll uses minimal memory allocation
- No garbage collection during active dodges
- Efficient vector normalization
- Optimized time calculations

## Browser Compatibility

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- IE11: Not supported (uses ES6 features)

## License

MIT
