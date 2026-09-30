'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { slugify } = require('./slugify.js');

test('lowercases and joins words with hyphens', () => {
  assert.equal(slugify('Hello World'), 'hello-world');
});

test('strips accents', () => {
  assert.equal(slugify('Café Déjà Vu'), 'cafe-deja-vu');
});

test('collapses runs of punctuation and spaces into a single hyphen', () => {
  assert.equal(slugify('Hello,   World!!'), 'hello-world');
});

test('does not produce leading or trailing hyphens', () => {
  assert.equal(slugify('  --Hello World--  '), 'hello-world');
});

test('rejects non-strings', () => {
  assert.throws(() => slugify(42), TypeError);
});

// Run tests
test('run all tests', async () => {
  await test('test 1', () => assert.equal(slugify('Hello World'), 'hello-world'));
  await test('test 2', () => assert.equal(slugify('Café Déjà Vu'), 'cafe-deja-vu'));
  await test('test 3', () => assert.equal(slugify('Hello,   World!!'), 'hello-world'));
  await test('test 4', () => assert.equal(slugify('  --Hello World--  '), 'hello-world'));
  await test('test 5', () => assert.throws(() => slugify(42), TypeError));
});
