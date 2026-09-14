'use strict';

/**
 * Converts a string into a URL-friendly slug by normalizing diacritics,
 * lowercasing characters, collapsing non-alphanumeric character sequences into single hyphens,
 * and trimming leading and trailing hyphens.
 *
 * @param {string} input - The input string to slugify.
 * @returns {string} The normalized slug.
 * @throws {TypeError} If the input is not a string.
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
