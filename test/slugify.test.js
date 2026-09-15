'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { slugify } = require('../src/slugify');

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
