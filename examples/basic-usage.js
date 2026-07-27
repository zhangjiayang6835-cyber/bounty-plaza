/**
 * Basic Usage Example for Dodge Roll System
 */

const {
  DodgeRoll,
  DodgeRollComponent,
  DodgeRollInputHandler
} = require('../src/index');

// Example 1: Using DodgeRoll directly
const dodgeRoll = new DodgeRoll({
  rollDuration: 0.5,
  rollSpeed: 15,
  rollCooldown: 1.0,
  iFrames: 0.3,
  onRollStart: (data) => console.log('Roll started:', data),
  onRollEnd: (data) => console.log('Roll ended:', data),
  onRollUpdate: (state) => console.log('Roll progress:', state.progress)
});

// Attempt a roll
const direction = { x: 1, y: 0 };
if (dodgeRoll.attemptRoll(direction, Date.now() / 1000)) {
  console.log('Roll initiated!');
}

// Update roll state
const state = dodgeRoll.update(Date.now() / 1000);
console.log('Current state:', state);

// Example 2: Using DodgeRollComponent with an entity
const entity = {
  position: { x: 100, y: 100 },
  onDodgeRollStart: (data) => console.log('Entity dodge roll started'),
  onDodgeRollEnd: (data) => console.log('Entity dodge roll ended'),
  onDodgeRollUpdate: (state) => {
    if (state.isInvulnerable) {
      console.log('Entity is invulnerable!');
    }
  }
};

const rollComponent = new DodgeRollComponent(entity, {
  rollDuration: 0.5,
  rollSpeed: 15,
  rollCooldown: 1.0,
  iFrames: 0.3,
  showTrail: true
});

// Trigger roll
if (rollComponent.roll({ x: 1, y: 0 })) {
  console.log('Entity is rolling!');
}

// Update component
rollComponent.update(0.016); // ~60 FPS

// Example 3: Using DodgeRollInputHandler
let currentDirection = { x: 0, y: 0 };

const inputHandler = new DodgeRollInputHandler({
  rollKey: ' ',
  enableDoubleTap: true,
  doubleTapThreshold: 0.3,
  getDirection: () => currentDirection,
  onRollInput: (input) => {
    console.log('Roll input received:', input);
    rollComponent.roll(input.direction);
  }
});

// Simulate direction input (e.g., from WASD keys)
function updateDirection(keys) {
  currentDirection = { x: 0, y: 0 };
  if (keys.w) currentDirection.y -= 1;
  if (keys.s) currentDirection.y += 1;
  if (keys.a) currentDirection.x -= 1;
  if (keys.d) currentDirection.x += 1;
}

// Game loop
function gameLoop() {
  const deltaTime = 0.016; // ~60 FPS

  // Update component
  rollComponent.update(deltaTime);

  // Check if roll is available
  if (rollComponent.canRoll()) {
    console.log('Roll is available');
  } else {
    const timeRemaining = rollComponent.getTimeUntilAvailable();
    console.log(`Roll available in ${timeRemaining.toFixed(2)}s`);
  }

  // Check invulnerability
  if (rollComponent.isInvulnerable()) {
    console.log('Entity is currently invulnerable');
  }
}

// Run game loop
setInterval(gameLoop, 16);
