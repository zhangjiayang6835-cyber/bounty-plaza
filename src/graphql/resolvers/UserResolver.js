const { AuthenticationError, ForbiddenError } = require('apollo-server-express');
const DataLoader = require('dataloader');
const { User, Order } = require('../models');
const rateLimit = require('express-rate-limit');

// Create rate limiter for user queries
const userQueryLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 30, // limit each IP to 30 requests per windowMs
  message: 'Too many requests from this IP, please try again later.'
});

// Create DataLoader for batch loading users
const userLoader = new DataLoader(async (userIds) => {
  const users = await User.find({ _id: { $in: userIds } });
  const userIdMap = {};
  users.forEach(user => {
    userIdMap[user._id] = user;
  });
  return userIds.map(id => userIdMap[id]);
});

const userResolvers = {
  Query: {
    user: async (_, { id }, { user }) => {
      // Apply rate limiting
      await new Promise((resolve, reject) => {
        userQueryLimiter(null, null, (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

      if (!user) {
        throw new AuthenticationError('Authentication required');
      }

      // Check if the requested user is the current user or an admin
      const requestedUser = await userLoader.load(id);
      if (!requestedUser) {
        throw new Error('User not found');
      }

      if (user.role !== 'admin' && user._id.toString() !== id) {
        throw new ForbiddenError('Access denied');
      }

      return requestedUser;
    },
    me: async (_, __, { user }) => {
      if (!user) {
        throw new AuthenticationError('Authentication required');
      }
      return userLoader.load(user._id);
    }
  },
  User: {
    orders: async (user, _, { user: currentUser }) => {
      if (!currentUser) {
        throw new AuthenticationError('Authentication required');
      }

      // Check if the current user has permission to access these orders
      if (currentUser.role !== 'admin' && currentUser._id.toString() !== user._id.toString()) {
        throw new ForbiddenError('Access denied');
      }

      // Return orders for this user
      return Order.find({ userId: user._id });
    }
  }
};

module.exports = userResolvers;