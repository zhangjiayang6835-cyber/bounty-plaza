const { defaultInstance } = require('./src/hello_world');

/**
 * Root executable entrypoint for the Hello World engine.
 */
function main() {
  defaultInstance.runCli(process.argv.slice(2), process.stdout);
}

if (require.main === module) {
  main();
}

module.exports = require('./src/hello_world');
