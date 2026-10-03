const normalize = (str) =>
  str
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');

module.exports = {
  slugify: (str) => {
    if (typeof str !== 'string') throw new TypeError('Expected a string');
    return normalize(str).replace(/[^\w\s-]/g, ' ').trim().replace(/\s+/g, '-');
  },
};
