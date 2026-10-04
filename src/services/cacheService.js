<content>
const NodeCache = require('node-cache');
const redis = require('redis');
const { promisify } = require('util');
const cacheConfig = require('../config/cacheConfig');
const { generateCacheKey } = require('../middleware/cacheMiddleware');

/**
 * Cache service for handling HTTP caching
 */
class CacheService {
  constructor() {
    this.initializeCache();
  }
  
  /**
   * Initialize cache storage
   */
  initializeCache() {
    if (cacheConfig.storage.engine === 'redis') {
      this.redisClient = redis.createClient({
        host: cacheConfig.storage.redis.host,
        port: cacheConfig.storage.redis.port,
        password: cacheConfig.storage.redis.password,
        db: cacheConfig.storage.redis.db
      });
      
      this.redisGet = promisify(this.redisClient.get).bind(this.redisClient);
      this.redisSet = promisify(this.redisClient.set).bind(this.redisClient);
      this.redisDel = promisify(this.redisClient.del).bind(this.redisClient);
      this.redisKeys = promisify(this.redisClient.keys).bind(this.redisClient);
    } else {
      this.memoryCache = new NodeCache({
        stdTTL: cacheConfig.storage.memory.maxAge / 1000,
        maxKeys: cacheConfig.storage.memory.max
      });
    }
  }
  
  /**
   * Get cached response
   * @param {Object} req - Express request object
   * @returns {Promise<Object|null>} Cached response or null
   */
  async get(req) {
    const cacheKey = generateCacheKey(req);
    
    try {
      if (this.redisClient) {
        const cached = await this.redisGet(cacheKey);
        return cached ? JSON.parse(cached) : null;
      } else {
        return this.memoryCache.get(cacheKey);
      }
    } catch (error) {
      console.error('Cache get error:', error);
      return null;
    }
  }
  
  /**
   * Set cached response
   * @param {Object} req - Express request object
   * @param {Object} response - Response object to cache
   * @param {number} ttl - Time to live in seconds
   */
  async set(req, response, ttl = null) {
    const cacheKey = generateCacheKey(req);
    const cacheTTL = ttl || cacheConfig.defaultTTL;
    
    try {
      // Clone response to avoid modifying original
      const cachedResponse = {
        status: response.status,
        headers: { ...response.headers },
        body: response.body
      };
      
      // Remove sensitive headers from cache
      this.sanitizeResponseHeaders(cachedResponse);
      
      if (this.redisClient) {
        await this.redisSet(cacheKey, JSON.stringify(cachedResponse), 'EX', cacheTTL);
      } else {
        this.memoryCache.set(cacheKey, cachedResponse, cacheTTL);
      }
    } catch (error) {
      console.error('Cache set error:', error);
    }
  }
  
  /**
   * Delete cached response
   * @param {Object} req - Express request object
   */
  async del(req) {
    const cacheKey = generateCacheKey(req);
    
    try {
      if (this.redisClient) {
        await this.redisDel(cacheKey);
      } else {
        this.memoryCache.del(cacheKey);
      }
    } catch (error) {
      console.error('Cache delete error:', error);
    }
  }
  
  /**
   * Clear all cached responses
   */
  async clear() {
    try {
      if (this.redisClient) {
        const keys = await this.redisKeys('*');
        if (keys.length > 0) {
          await this.redisDel(keys);
        }
      } else {
        this.memoryCache.flushAll();
      }
    } catch (error) {
      console.error('Cache clear error:', error);
    }
  }
  
  /**
   * Sanitize response headers to prevent information leakage
   * @param {Object} response - Response object
   */
  sanitizeResponseHeaders(response) {
    const sensitiveHeaders = [
      'set-cookie',
      'x-powered-by',
      'server',
      'x-frame-options',
      'x-content-type-options',
      'x-xss-protection'
    ];
    
    for (const header of sensitiveHeaders) {
      delete response.headers[header];
    }
  }
}

module.exports = new CacheService();
</content>