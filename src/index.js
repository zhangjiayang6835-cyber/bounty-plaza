/**
 * Bounty Plaza — Entry point
 *
 * A lightweight platform for managing GitHub bounties, claims, and reward tracking.
 */

const { GITHUB_TOKEN, PORT = '3000' } = process.env;

/**
 * Bootstraps the application.
 * Logs a startup message with the configured port.
 */
function bootstrap() {
  const timestamp = new Date().toISOString();
  console.log(`[BountyPlaza] Starting at ${timestamp} on port ${PORT}`);
  console.log(`[BountyPlaza] GitHub token configured: ${!!GITHUB_TOKEN}`);
}

bootstrap();

module.exports = { bootstrap };
