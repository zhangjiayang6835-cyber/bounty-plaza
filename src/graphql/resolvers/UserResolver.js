const { AuthenticationError, ForbiddenError } = require('apollo-server-express');
const DataLoader = require('dataloader');
const { User, Order } = require('../models');

// Create a DataLoader for fetching users with authentication checks
const userLoader = new DataLoader(async (keys) => {
  const users = await User.find({ _id: { $in: keys } });
  const userMap = {};
  users.forEach(user => {
    userMap[user._id] = user;
  });
  return keys.map(key => userMap[key]);
});

const userResolvers = {
  Query: {
    // Get current user
    me: async (parent, args, { user }) => {
      if (!user) {
        throw new AuthenticationError('Authentication required');
      }
      return userLoader.load(user.id);
    },
    
    // Get user by ID - only accessible for own profile or admins
    user: async (parent, { id }, { user }) => {
      if (!user) {
        throw new AuthenticationError('Authentication required');
      }
      
      const targetUser = await userLoader.load(id);
      
      // Check if the user is accessing their own profile or is an admin
      if (user.id !== id && user.role !== 'ADMIN') {
        throw new ForbiddenError('Access denied');
      }
      
      return targetUser;
    },
    
    // Get all users (admin only)
    users: async (parent, args, { user }) => {
      if (!user || user.role !== 'ADMIN') {
        throw new AuthenticationError('Admin access required');
      }
      
      return User.find({});
    }
  },
  
  User: {
    // Orders field resolver with ownership check
    orders: async (parent, args, { user }) => {
      if (!user) {
        throw new AuthenticationError('Authentication required');
      }
      
      // Check if the user is accessing their own orders or is an admin
      if (user.id !== parent.id && user.role !== 'ADMIN') {
        throw new ForbiddenError('Access denied');
      }
      
      return Order.find({ userId: parent.id });
    }
  }
};

module.exports = userResolvers;