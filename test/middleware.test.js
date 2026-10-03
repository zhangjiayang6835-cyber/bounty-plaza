/**
 * Test suite for GraphQL complexity middleware
 */

const { GraphQLSchema, GraphQLObjectType, GraphQLString } = require('graphql');
const { ComplexityMiddleware } = require('../graphql');

describe('ComplexityMiddleware', () => {
  const testSchema = new GraphQLSchema({
    query: new GraphQLObjectType({
      name: 'Query',
      fields: {
        hello: { type: GraphQLString }
      }
    })
  });

  const middleware = new ComplexityMiddleware({
    maxDepth: 3,
    maxComplexity: 10,
    maxRequests: 5,
    maxComplexityPerWindow: 20,
    windowMs: 1000
  });

  test('should allow simple queries', () => {
    const query = `
      query {
        hello
      }
    `;
    
    const document = require('graphql').parse(query);
    const context = { ip: '127.0.0.1' };
    
    expect(() => {
      middleware.middleware(testSchema)({}, {}, context, { document, variableValues: {} });
    }).not.toThrow();
  });

  test('should reject complex queries', () => {
    const query = `
      query {
        user {
          posts {
            comments {
              id
              text
            }
          }
        }
      }
    `;
    
    const document = require('graphql').parse(query);
    const context = { ip: '127.0.0.1' };
    
    expect(() => {
      middleware.middleware(testSchema)({}, {}, context, { document, variableValues: {} });
    }).toThrow('Query complexity limit');
  });

  test('should enforce rate limiting', (done) => {
    const query = `
      query {
        hello
      }
    `;
    
    const document = require('graphql').parse(query);
    const context = { ip: '127.0.0.1' };
    
    // Make 5 requests (should pass)
    for (let i = 0; i < 5; i++) {
      expect(() => {
        middleware.middleware(testSchema)({}, {}, context, { document, variableValues: {} });
      }).not.toThrow();
    }
    
    // 6th request should fail
    expect(() => {
      middleware.middleware(testSchema)({}, {}, context, { document, variableValues: {} });
    }).toThrow('Rate limit exceeded');
    
    setTimeout(done, 1100); // Wait for window to reset
  });

  test('should provide rate limit status', () => {
    const context = { ip: '127.0.0.1' };
    const status = middleware.getRateLimitStatus(context);
    
    expect(status).toHaveProperty('remaining');
    expect(status).toHaveProperty('complexityRemaining');
    expect(status).toHaveProperty('resetTime');
  });
});