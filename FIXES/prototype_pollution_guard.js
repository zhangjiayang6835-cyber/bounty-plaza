function safeDeepMerge(target, source) {
  for (const key in source) {
    if (Object.prototype.hasOwnProperty.call(source, key)) {
      // Block prototype pollution vectors (__proto__, constructor, prototype)
      if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
        continue;
      }
      if (typeof source[key] === 'object' && source[key] !== null && !Array.isArray(source[key])) {
        if (!target[key]) target[key] = {};
        safeDeepMerge(target[key], source[key]);
      } else {
        target[key] = source[key];
      }
    }
  }
  return target;
}

module.exports = safeDeepMerge;
