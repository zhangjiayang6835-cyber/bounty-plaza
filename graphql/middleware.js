/**
 * GraphQL Complexity Middleware
 * Implements rate limiting based on query complexity
 */

const QueryComplexity = require('./complexity');
const { createGraphQLError } = require('graphql');

class ComplexityMiddleware {
  constructor(options = {}) {
    this.complexityAnalyzer = new QueryComplexity(options);
    this.rateLimitStore = options.rateLimitStore || new Map();
    this.windowMs = options.windowMs || 60000; // 1 minute
    this.maxRequests = options.maxRequests || 100;
    this.maxComplexityPerWindow = options.maxComplexityPerWindow || 1000;
  }

  /**
   * Create GraphQL middleware for complexity analysis
   */
  middleware(schema) {
    return (root, args, context, info) => {
      const { document, variableValues } = info;
      
      try {
        // Calculate complexity
        const complexity = this.complexityAnalyzer.getComplexity(document, schema);
        
        // Validate complexity
        this.complexityAnalyzer.validateComplexity(complexity);
        
        // Apply rate limiting based on complexity
        this.applyRateLimiting(context, complexity.score);
        
        return root;
      } catch (error) {
        throw createGraphQLError(error.message, {
          nodes: document,
          extensions: {
            code: 'GRAPHQL_VALIDITY_ERROR',
            complexity: complexity ? complexity.score : 0
          }
        });
      }
    };
  }

  /**
   * Create GraphQL batch query middleware
   */
  batchMiddleware(schema) {
    return async (batchRequests, context) => {
      try {
        // Calculate total complexity for batch
        const complexity = this.complexityAnalyzer.getBatchComplexity(
          batchRequests.map(req => ({
            document: req.document,
            variables: req.variables
          })),
          schema
        );
        
        // Validate complexity
        this.complexityAnalyzer.validateComplexity(complexity);
        
        // Apply rate limiting based on total complexity
        this.applyRateLimiting(context, complexity.score);
        
        return batchRequests;
      } catch (error) {
        throw new Error(`Batch query complexity error: ${error.message}`);
      }
    };
  }

  /**
   * Apply rate limiting based on complexity
   */
  applyRateLimiting(context, complexity) {
    const clientId = context.clientId || context.ip || 'anonymous';
    const now = Date.now();
    
    // Clean expired entries
    this.cleanupExpiredEntries(now);
    
    // Get or create rate limit entry
    if (!this.rateLimitStore.has(clientId)) {
      this.rateLimitStore.set(clientId, {
        count: 0,
        complexity: 0,
        resetTime: now + this.windowMs
      });
    }
    
    const entry = this.rateLimitStore.get(clientId);
    
    // Check if window has expired
    if (now > entry.resetTime) {
      entry.count = 0;
      entry.complexity = 0;
      entry.resetTime = now + this.windowMs;
    }
    
    // Check limits
    if (entry.count >= this.maxRequests) {
      throw new Error(`Rate limit exceeded: ${this.maxRequests} requests per ${this.windowMs}ms`);
    }
    
    if (entry.complexity + complexity > this.maxComplexityPerWindow) {
      throw new Error(`Complexity rate limit exceeded: ${this.maxComplexityPerWindow} complexity points per ${this.windowMs}ms`);
    }
    
    // Update counters
    entry.count++;
    entry.complexity += complexity;
  }

  /**
   * Clean up expired rate limit entries
   */
  cleanupExpiredEntries(now) {
    for (const [clientId, entry] of this.rateLimitStore.entries()) {
      if (now > entry.resetTime) {
        this.rateLimitStore.delete(clientId);
      }
    }
  }

  /**
   * Get current rate limit status
   */
  getRateLimitStatus(context) {
    const clientId = context.clientId || context.ip || 'anonymous';
    const now = Date.now();
    
    if (!this.rateLimitStore.has(clientId)) {
      return {
        remaining: this.maxRequests,
        complexityRemaining: this.maxComplexityPerWindow,
        resetTime: now + this.windowMs
      };
    }
    
    const entry = this.rateLimitStore.get(clientId);
    
    return {
      remaining: Math.max(0, this.maxRequests - entry.count),
      complexityRemaining: Math.max(0, this.maxComplexityPerWindow - entry.complexity),
      resetTime: entry.resetTime
    };
  }
}

module.exports = ComplexityMiddleware;