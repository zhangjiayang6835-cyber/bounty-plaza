const { AuthenticationError } = require('apollo-server-express');
const rateLimit = require('express-rate-limit');

// Create a rate limiter for GraphQL queries
const createRateLimit = (maxRequests, windowMs) => {
  return rateLimit({
    max: maxRequests,
    windowMs: windowMs,
    message: 'Too many requests, please try again later',
    standardHeaders: true,
    legacyHeaders: false,
  });
};

// Apply rate limiting to GraphQL queries
const queryRateLimit = createRateLimit(100, 15 * 60 * 1000); // 100 requests per 15 minutes

const queryResolvers = {
  Query: {
    // Add a root query that can be used to apply rate limiting
    _rateLimitCheck: async (parent, args, { user }) => {
      // This is a dummy query to check if the user is authenticated
      if (!user) {
        throw new AuthenticationError('Authentication required');
      }
      return true;
    }
  }
};

// Middleware to apply rate limiting to GraphQL queries
const applyRateLimit = (resolve, root, args, context, info) => {
  // Apply rate limiting to all queries except introspection
  if (info.fieldName !== '__schema' && info.fieldName !== '__type') {
    // In a real implementation, you would use the actual rate limiting middleware
    // Here we're just simulating the check
    const now = Date.now();
    const userKey = context.user ? `user_${context.user.id}` : 'anonymous';
    
    // Check if the user has exceeded the rate limit
    if (context.rateLimit && context.rateLimit[userKey] && context.rateLimit[userKey] > now) {
      throw new Error('Rate limit exceeded');
    }
    
    // Set the rate limit for the user
    if (!context.rateLimit) {
      context.rateLimit = {};
    }
    context.rateLimit[userKey] = now + 15 * 60 * 1000; // 15 minutes from now
  }
  
  return resolve(root, args, context, info);
};

module.exports = {
  queryResolvers,
  applyRateLimit
};