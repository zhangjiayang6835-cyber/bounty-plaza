const { AuthenticationError, ForbiddenError } = require('apollo-server-express');
const DataLoader = require('dataloader');
const { Order, Item } = require('../models');
const rateLimit = require('express-rate-limit');

// Create rate limiter for order queries
const orderQueryLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 60, // limit each IP to 60 requests per windowMs
  message: 'Too many requests from this IP, please try again later.'
});

// Create DataLoader for batch loading orders
const orderLoader = new DataLoader(async (orderIds) => {
  const orders = await Order.find({ _id: { $in: orderIds } });
  const orderIdMap = {};
  orders.forEach(order => {
    orderIdMap[order._id] = order;
  });
  return orderIds.map(id => orderIdMap[id]);
});

// Create DataLoader for batch loading items
const itemLoader = new DataLoader(async (itemIds) => {
  const items = await Item.find({ _id: { $in: itemIds } });
  const itemIdMap = {};
  items.forEach(item => {
    itemIdMap[item._id] = item;
  });
  return itemIds.map(id => itemIdMap[id]);
});

const orderResolvers = {
  Query: {
    order: async (_, { id }, { user }) => {
      // Apply rate limiting
      await new Promise((resolve, reject) => {
        orderQueryLimiter(null, null, (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

      if (!user) {
        throw new AuthenticationError('Authentication required');
      }

      const order = await orderLoader.load(id);
      if (!order) {
        throw new Error('Order not found');
      }

      // Check if the current user has permission to access this order
      if (user.role !== 'admin' && user._id.toString() !== order.userId.toString()) {
        throw new ForbiddenError('Access denied');
      }

      return order;
    }
  },
  Order: {
    items: async (order, _, { user }) => {
      if (!user) {
        throw new AuthenticationError('Authentication required');
      }

      // Check if the current user has permission to access this order
      if (user.role !== 'admin' && user._id.toString() !== order.userId.toString()) {
        throw new ForbiddenError('Access denied');
      }

      // Return items for this order
      return Item.find({ orderId: order._id });
    },
    user: async (order, _, { user }) => {
      if (!user) {
        throw new AuthenticationError('Authentication required');
      }

      // Check if the current user has permission to access this order
      if (user.role !== 'admin' && user._id.toString() !== order.userId.toString()) {
        throw new ForbiddenError('Access denied');
      }

      return orderLoader.load(order.userId);
    }
  },
  Item: {
    order: async (item, _, { user }) => {
      if (!user) {
        throw new AuthenticationError('Authentication required');
      }

      // Check if the current user has permission to access this item
      const order = await orderLoader.load(item.orderId);
      if (user.role !== 'admin' && user._id.toString() !== order.userId.toString()) {
        throw new ForbiddenError('Access denied');
      }

      return order;
    }
  }
};

module.exports = orderResolvers;