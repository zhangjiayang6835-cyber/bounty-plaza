/**
 * Basic usage example for GraphQL complexity analyzer
 */

const { GraphQLSchema, GraphQLObjectType, GraphQLString, GraphQLList } = require('graphql');
const { ComplexityMiddleware } = require('../graphql');

// Create a sample schema
const userType = new GraphQLObjectType({
  name: 'User',
  fields: {
    id: { type: GraphQLString },
    name: { type: GraphQLString },
    email: { type: GraphQLString }
  }
});

const postType = new GraphQLObjectType({
  name: 'Post',
  fields: {
    id: { type: GraphQLString },
    title: { type: GraphQLString },
    content: { type: GraphQLString },
    author: { type: userType }
  }
});

const schema = new GraphQLSchema({
  query: new GraphQLObjectType({
    name: 'Query',
    fields: {
      users: {
        type: new GraphQLList(userType),
        resolve: () => []
      },
      posts: {
        type: new GraphQLList(postType),
        resolve: () => []
      }
    }
  })
});

// Create middleware with custom limits
const complexityMiddleware = new ComplexityMiddleware({
  maxDepth: 5,
  maxComplexity: 100,
  maxRequests: 50,
  maxComplexityPerWindow: 500,
  windowMs: 60000,
  costPerField: 1,
  ignore: ['users'] // Don't count complexity for users field
});

// Example GraphQL queries
const simpleQuery = `
  query {
    users {
      id
      name
    }
  }
`;

const complexQuery = `
  query {
    posts {
      id
      title
      author {
        id
        name
        email
      }
    }
  }
`;

const batchQuery = [
  { query: simpleQuery },
  { query: complexQuery }
];

// Example usage with Express.js
const express = require('express');
const { graphqlHTTP } = require('express-graphql');
const app = express();

app.use('/graphql', graphqlHTTP({
  schema: schema,
  rootValue: {},
  context: { ip: '127.0.0.1' },
  customFormatErrorFn: (err) => {
    if (err.extensions?.code === 'GRAPHQL_VALIDITY_ERROR') {
      return {
        message: err.message,
        extensions: {
          code: 'COMPLEXITY_ERROR',
          complexity: err.extensions.complexity
        }
      };
    }
    return err;
  },
  // Apply complexity middleware
  validationRules: [
    // Add complexity validation rule here
  ]
}));

// For batch queries, you would use a separate endpoint
app.post('/graphql/batch', express.json(), (req, res) => {
  try {
    // Apply batch complexity middleware
    complexityMiddleware.batchMiddleware(schema)(req.body, { ip: req.ip });
    
    // Process batch queries
    res.json({ success: true });
  } catch (err) {
    res.status(429).json({
      success: false,
      message: err.message,
      extensions: {
        code: 'COMPLEXITY_ERROR'
      }
    });
  }
});

app.listen(3000, () => {
  console.log('GraphQL server running on http://localhost:3000');
});