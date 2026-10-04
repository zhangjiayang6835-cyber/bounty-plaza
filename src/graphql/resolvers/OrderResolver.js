const { AuthenticationError, ForbiddenError } = require('apollo-server-express');
const DataLoader = require('dataloader');
const { Order, OrderItem } = require('../models');

// Create a DataLoader for fetching orders with authentication checks
const orderLoader = new DataLoader(async (keys) => {
  const orders = await Order.find({ _id: { $in: keys } });
  const orderMap = {};
  orders.forEach(order => {
    orderMap[order._id] = order;
  });
  return keys.map(key => orderMap[key]);
});

// Create a DataLoader for fetching order items with authentication checks
const orderItemLoader = new DataLoader(async (keys) => {
  const items = await OrderItem.find({ _id: { $in: keys } });
  const itemMap = {};
  items.forEach(item => {
    itemMap[item._id] = item;
  });
  return keys.map(key => itemMap[key]);
});

const orderResolvers = {
  Query: {
    // Get order by ID with ownership check
    order: async (parent, { id }, { user }) => {
      if (!user) {
        throw new AuthenticationError('Authentication required');
      }
      
      const order = await orderLoader.load(id);
      
      // Check if the user owns the order or is an admin
      if (user.id !== order.userId && user.role !== 'ADMIN') {
        throw new ForbiddenError('Access denied');
      }
      
      return order;
    },
    
    // Get all orders (admin only)
    orders: async (parent, args, { user }) => {
      if (!user || user.role !== 'ADMIN') {
        throw new AuthenticationError('Admin access required');
      }
      
      return Order.find({});
    }
  },
  
  Order: {
    // Order items field resolver with ownership check
    items: async (parent, args, { user }) => {
      if (!user) {
        throw new AuthenticationError('Authentication required');
      }
      
      // Check if the user owns the order or is an admin
      if (user.id !== parent.userId && user.role !== 'ADMIN') {
        throw new ForbiddenError('Access denied');
      }
      
      return OrderItem.find({ orderId: parent.id });
    }
  }
};

module.exports = orderResolvers;