'use strict';

/**
 * Turn a human title into a URL slug.
 *   "Hello, World!"  -> "hello-world"
 *   "  Ünïcode Café " -> "unicode-cafe"
 */
function slugify(input) {
  if (typeof input !== 'string') {
    throw new TypeError('slugify expects a string');
  }
  return input
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

module.exports = { slugify };
