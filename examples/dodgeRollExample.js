const DodgeRoll = require('../src/mechanics/dodgeRoll');
const PlayerController = require('../src/player/playerController');
const DodgeRollUI = require('../src/ui/dodgeRollUI');

/**
 * Example: Basic Dodge Roll Implementation
 */
class ExamplePlayer {
  constructor() {
    this.position = { x: 0, y: 0 };
    this.isInvulnerable = false;
  }

  setPosition(pos) {
    this.position = pos;
    console.log(`Player moved to: (${pos.x.toFixed(2)}, ${pos.y.toFixed(2)})`);
  }

  setInvulnerable(state) {
    this.isInvulnerable = state;
    if (state) {
      console.log('Player is now invulnerable!');
    }
  }

  onDodgeStart() {
    console.log('Dodge roll initiated!');
  }
}

// Create player and controller
const player = new ExamplePlayer();
const controller = new PlayerController(player, {
  dodgeConfig: {
    duration: 0.5,
    cooldown: 1.0,
    distance: 10,
    invulnerabilityFrames: 0.3
  }
});

// Simulate game loop
let gameTime = 0;
const deltaTime = 0.016; // ~60 FPS

function gameLoop() {
  gameTime += deltaTime;

  // Update player
  controller.update(deltaTime);

  // Get dodge state
  const dodgeState = controller.getDodgeState();
  console.log(`[${gameTime.toFixed(2)}s] Dodge State:`, {
    isActive: dodgeState.isActive,
    canDodge: dodgeState.canDodge,
    remainingCooldown: dodgeState.remainingCooldown.toFixed(2),
    isInvulnerable: dodgeState.isInvulnerable
  });
}

// Simulate input at specific times
setTimeout(() => {
  console.log('\n--- Initiating dodge roll ---');
  controller.handleDodgeInput({ x: 1, y: 0 });
}, 100);

// Run game loop
const loopInterval = setInterval(gameLoop, 16);

// Stop after 5 seconds
setTimeout(() => {
  clearInterval(loopInterval);
  console.log('\n--- Example complete ---');
}, 5000);

module.exports = { ExamplePlayer, controller };