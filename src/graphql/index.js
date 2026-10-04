const { ApolloServer } = require('apollo-server-express');
const { makeExecutableSchema } = require('graphql-tools');
const typeDefs = require('./typeDefs');
const userResolvers = require('./resolvers/UserResolver');
const orderResolvers = require('./resolvers/OrderResolver');
const { queryResolvers, applyRateLimit } = require('./resolvers/Query');
const { authenticate } = require('../middleware/auth');

const resolvers = {
  Query: {
    ...userResolvers.Query,
    ...orderResolvers.Query,
    ...queryResolvers.Query
  },
  User: {
    ...userResolvers.User
  },
  Order: {
    ...orderResolvers.Order
  }
};

const schema = makeExecutableSchema({
  typeDefs,
  resolvers
});

const createGraphQLServer = (app) => {
  const server = new ApolloServer({
    schema,
    context: ({ req }) => {
      // Apply authentication middleware
      return authenticate(req);
    },
    formatError: (err) => {
      // Don't expose internal server errors
      if (err.originalError instanceof Error) {
        return {
          message: err.message,
          locations: err.locations,
          path: err.path,
          extensions: {
            code: err.extensions?.code || 'INTERNAL_SERVER_ERROR'
          }
        };
      }
      return err;
    }
  });

  server.applyMiddleware({ app, path: '/graphql' });
  
  return server;
};

module.exports = createGraphQLServer;