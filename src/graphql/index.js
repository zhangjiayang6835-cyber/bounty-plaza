const { ApolloServer, gql } = require('apollo-server-express');
const typeDefs = require('./typeDefs');
const resolvers = require('./resolvers');
const { authMiddleware } = require('../middleware/auth');

const server = new ApolloServer({
  typeDefs,
  resolvers,
  context: ({ req }) => {
    // Use auth middleware to get user context
    return authMiddleware(req);
  },
  introspection: process.env.NODE_ENV === 'development',
  playground: process.env.NODE_ENV === 'development'
});

module.exports = server;