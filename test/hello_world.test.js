const test = require('node:test');
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const path = require('node:path');
const { HelloWorld, FORMATS, GREETINGS, greet } = require('../src/hello_world');

test('HelloWorld default greeting returns "Hello, World!"', () => {
  const engine = new HelloWorld();
  const result = engine.greet();
  assert.equal(result, 'Hello, World!');
});

test('HelloWorld top-level greet helper returns default greeting', () => {
  const result = greet();
  assert.equal(result, 'Hello, World!');
});

test('HelloWorld custom target greeting', () => {
  const engine = new HelloWorld();
  const result = engine.greet({ target: 'OmniBlocks' });
  assert.equal(result, 'Hello, OmniBlocks!');
});

test('HelloWorld shout mode converts greeting to uppercase', () => {
  const engine = new HelloWorld();
  const result = engine.greet({ target: 'BountyPlaza', shout: true });
  assert.equal(result, 'HELLO, BOUNTYPLAZA!');
});

test('HelloWorld custom punctuation', () => {
  const engine = new HelloWorld();
  const result = engine.greet({ target: 'Developer', punctuation: '?' });
  assert.equal(result, 'Hello, Developer?');
});

test('HelloWorld multilingual support for Chinese', () => {
  const engine = new HelloWorld();
  const result = engine.greet({ language: 'zh', target: '世界' });
  assert.equal(result, '你好, 世界!');
});

test('HelloWorld multilingual support for Spanish', () => {
  const engine = new HelloWorld();
  const result = engine.greet({ language: 'es', target: 'Mundo' });
  assert.equal(result, 'Hola, Mundo!');
});

test('HelloWorld multilingual support for French', () => {
  const engine = new HelloWorld();
  const result = engine.greet({ language: 'fr', target: 'Monde' });
  assert.equal(result, 'Bonjour, Monde!');
});

test('HelloWorld multilingual support for Japanese', () => {
  const engine = new HelloWorld();
  const result = engine.greet({ language: 'ja', target: '世界' });
  assert.equal(result, 'こんにちは, 世界!');
});

test('HelloWorld fallback to English on unknown language code', () => {
  const engine = new HelloWorld();
  const result = engine.greet({ language: 'unknown_lang' });
  assert.equal(result, 'Hello, World!');
});

test('HelloWorld dynamic language registration', () => {
  const engine = new HelloWorld();
  engine.registerLanguage('eo', 'Saluton');
  assert.equal(engine.greet({ language: 'eo', target: 'Mondo' }), 'Saluton, Mondo!');
});

test('HelloWorld registerLanguage validation rejects invalid types', () => {
  const engine = new HelloWorld();
  assert.throws(() => engine.registerLanguage('', 'Test'), TypeError);
  assert.throws(() => engine.registerLanguage('eo', null), TypeError);
});

test('HelloWorld supported languages list', () => {
  const engine = new HelloWorld();
  const languages = engine.getSupportedLanguages();
  assert.ok(Array.isArray(languages));
  assert.ok(languages.includes('en'));
  assert.ok(languages.includes('zh'));
  assert.ok(languages.includes('es'));
});

test('HelloWorld JSON format output structure', () => {
  const engine = new HelloWorld();
  const raw = engine.greet({ format: FORMATS.JSON, target: 'Tester' });
  const parsed = JSON.parse(raw);
  assert.equal(parsed.greeting, 'Hello');
  assert.equal(parsed.target, 'Tester');
  assert.equal(parsed.message, 'Hello, Tester!');
  assert.equal(parsed.language, 'en');
  assert.equal(parsed.shout, false);
});

test('HelloWorld Markdown format output', () => {
  const engine = new HelloWorld();
  const result = engine.greet({ format: FORMATS.MARKDOWN, target: 'GitHub' });
  assert.equal(result, '# Hello, GitHub!');
});

test('HelloWorld HTML format output', () => {
  const engine = new HelloWorld();
  const result = engine.greet({ format: FORMATS.HTML, target: 'Web' });
  assert.equal(result, '<div class="greeting"><h1>Hello, Web!</h1></div>');
});

test('HelloWorld ANSI format output contains escape codes', () => {
  const engine = new HelloWorld();
  const result = engine.greet({ format: FORMATS.ANSI, target: 'Terminal' });
  assert.ok(result.startsWith('\x1b[1;32m'));
  assert.ok(result.endsWith('\x1b[0m'));
});

test('HelloWorld ASCII Banner format output', () => {
  const engine = new HelloWorld();
  const banner = engine.greet({ format: FORMATS.ASCII_BANNER, target: 'Test' });
  const lines = banner.split('\n');
  assert.equal(lines.length, 5);
  assert.ok(lines[0].startsWith('+'));
  assert.ok(lines[2].includes('Hello, Test!'));
});

test('HelloWorld CLI execution returns expected stdout', () => {
  const scriptPath = path.resolve(__dirname, '../hello_world.js');
  const output = execFileSync(process.execPath, [scriptPath], { encoding: 'utf-8' });
  assert.equal(output.trim(), 'Hello, World!');
});

test('HelloWorld CLI execution with language flag', () => {
  const scriptPath = path.resolve(__dirname, '../hello_world.js');
  const output = execFileSync(process.execPath, [scriptPath, '--lang', 'es', '--target', 'Mundo'], { encoding: 'utf-8' });
  assert.equal(output.trim(), 'Hola, Mundo!');
});

test('HelloWorld CLI execution with json flag', () => {
  const scriptPath = path.resolve(__dirname, '../hello_world.js');
  const output = execFileSync(process.execPath, [scriptPath, '--json'], { encoding: 'utf-8' });
  const parsed = JSON.parse(output);
  assert.equal(parsed.message, 'Hello, World!');
});

test('HelloWorld CLI execution with help flag', () => {
  const scriptPath = path.resolve(__dirname, '../hello_world.js');
  const output = execFileSync(process.execPath, [scriptPath, '--help'], { encoding: 'utf-8' });
  assert.ok(output.includes('Usage: hello_world'));
});
