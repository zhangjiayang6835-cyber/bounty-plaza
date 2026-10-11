/**
 * Bounty Plaza - Main Application Entry Point
 * A comprehensive bounty hunting platform
 */

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
const path = require('path');

// Initialize modes
const modeRegistry = require('./modes');

// Initialize Express app
const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // limit each IP to 100 requests per windowMs
});
app.use(limiter);

// Routes
app.get('/api/health', (req, res) => {
  const mode = modeRegistry.getCurrentMode();
  res.json({
    status: 'healthy',
    mode: modeRegistry.currentMode,
    timestamp: new Date().toISOString()
  });
});

app.get('/api/modes', (req, res) => {
  res.json({
    currentMode: modeRegistry.currentMode,
    availableModes: modeRegistry.listModes()
  });
});

app.post('/api/modes/:name', (req, res) => {
  try {
    const mode = modeRegistry.setMode(req.params.name);
    res.json({ success: true, mode: mode.name });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// SaaS-specific routes
app.get('/api/tenants', (req, res) => {
  const saasMode = modeRegistry.getMode('saas');
  if (!saasMode || !saasMode.enabled) {
    return res.status(400).json({ error: 'SaaS mode is not enabled' });
  }
  res.json(saasMode.listTenants());
});

app.post('/api/tenants', (req, res) => {
  const saasMode = modeRegistry.getMode('saas');
  if (!saasMode || !saasMode.enabled) {
    return res.status(400).json({ error: 'SaaS mode is not enabled' });
  }
  try {
    const tenant = saasMode.registerTenant(req.body.id, req.body.tier);
    res.status(201).json(tenant);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

app.delete('/api/tenants/:id', (req, res) => {
  const saasMode = modeRegistry.getMode('saas');
  if (!saasMode || !saasMode.enabled) {
    return res.status(400).json({ error: 'SaaS mode is not enabled' });
  }
  try {
    const tenant = saasMode.unregisterTenant(req.params.id);
    res.json({ success: true, tenant });
  } catch (error) {
    res.status(404).json({ error: error.message });
  }
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Start server
app.listen(PORT, () => {
  console.log(`Bounty Plaza running on port ${PORT} in ${modeRegistry.currentMode} mode`);
});

module.exports = app;
