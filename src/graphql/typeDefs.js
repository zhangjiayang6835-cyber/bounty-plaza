const gql = require('graphql-tag');

const typeDefs = gql`
  type User {
    id: ID!
    name: String!
    email: String!
    role: String!
    orders: [Order!]!
  }

  type Order {
    id: ID!
    userId: ID!
    items: [OrderItem!]!
    total: Float!
    createdAt: String!
    updatedAt: String!
  }

  type OrderItem {
    id: ID!
    orderId: ID!
    name: String!
    price: Float!
    quantity: Int!
  }

  type Query {
    me: User
    user(id: ID!): User
    users: [User!]!
    order(id: ID!): Order
    orders: [Order!]!
    _rateLimitCheck: Boolean
  }

  type Mutation {
    # Add mutations as needed
  }
`;

module.exports = typeDefs;