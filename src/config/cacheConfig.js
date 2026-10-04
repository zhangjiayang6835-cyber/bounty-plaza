<content>
/**
 * Cache configuration settings
 */
const cacheConfig = {
  // Default cache time in seconds
  defaultTTL: 3600,
  
  // Maximum cache time in seconds
  maxTTL: 86400,
  
  // Cache key settings
  cacheKey: {
    // Headers that should be included in cache key
    keyedHeaders: [
      'accept',
      'accept-encoding',
      'accept-language',
      'cookie',
      'x-forwarded-host',
      'x-forwarded-proto',
      'host'
    ],
    
    // Headers that should be excluded from cache key
    excludedHeaders: [
      'user-agent',
      'via',
      'x-forwarded-for',
      'x-real-ip'
    ],
    
    // Headers that should be normalized
    normalizedHeaders: {
      'accept-encoding': (value) => {
        const encodings = value.toLowerCase().split(',').map(e => e.trim());
        const normalized = encodings.sort().join(', ');
        return normalized.includes('gzip') || normalized.includes('deflate') 
          ? 'gzip, deflate' 
          : normalized;
      },
      'user-agent': (value) => {
        return value.toLowerCase().includes('mobile') ? 'mobile' : 'desktop';
      }
    }
  },
  
  // Security settings
  security: {
    // Block suspicious headers
    blockSuspiciousHeaders: true,
    
    // List of suspicious headers to block
    suspiciousHeaders: [
      'x-http-method-override',
      'x-method-override',
      'x-rewrite-url'
    ],
    
    // Max header size in bytes
    maxHeaderSize: 8192,
    
    // Enable header sanitization
    sanitizeHeaders: true
  },
  
  // Cache storage settings
  storage: {
    // Default storage engine
    engine: 'memory',
    
    // Redis configuration if using Redis
    redis: {
      host: process.env.REDIS_HOST || 'localhost',
      port: process.env.REDIS_PORT || 6379,
      password: process.env.REDIS_PASSWORD || null,
      db: process.env.REDIS_DB || 0
    },
    
    // Memory cache settings
    memory: {
      max: 100, // Maximum number of items
      maxAge: 3600000 // Maximum age in milliseconds
    }
  }
};

module.exports = cacheConfig;
</content>