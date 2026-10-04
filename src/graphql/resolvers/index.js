const { mergeResolvers } = require('@graphql-tools/merge');
const userResolvers = require('./UserResolver');
const orderResolvers = require('./OrderResolver');

module.exports = mergeResolvers([
  userResolvers,
  orderResolvers
]);