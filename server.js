const express = require('express');
const helmet = require('helmet');
const path = require('path');
const app = express();

// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "https://*.cdn.com"],
      imgSrc: ["'self'", "data:", "https:"],
    },
  },
  xContentTypeOptions: true, // Implements X-Content-Type-Options
}));

// Middleware to set proper Cache-Control headers
const cacheControl = (req, res, next) => {
  // For sensitive pages, disable caching
  if (req.path.startsWith('/account') || req.path.startsWith('/admin')) {
    res.set('Cache-Control', 'no-store, no-cache, must-revalidate, private');
    res.set('Pragma', 'no-cache');
    res.set('Expires', '0');
  } else {
    // For static assets, set appropriate caching
    res.set('Cache-Control', 'public, max-age=31536000, immutable');
  }
  next();
};

// Apply cache control middleware
app.use(cacheControl);

// Static file serving with proper content type handling
app.use(express.static('public', {
  setHeaders: (res, filePath) => {
    const ext = path.extname(filePath).toLowerCase();
    
    // Set proper content type based on file content, not extension
    if (ext === '.css') {
      res.set('Content-Type', 'text/css');
    } else if (ext === '.js') {
      res.set('Content-Type', 'application/javascript');
    } else if (ext === '.html') {
      res.set('Content-Type', 'text/html');
    }
    
    // Set X-Content-Type-Options for static files
    res.set('X-Content-Type-Options', 'nosniff');
  }
}));

// Sample sensitive page
app.get('/account/settings', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Account Settings</title>
      <style>
        body { font-family: Arial, sans-serif; }
        .token { display: none; }
      </style>
    </head>
    <body>
      <h1>Account Settings</h1>
      <p>Session Token: <span class="token">${req.sessionID || 'SESSION_TOKEN_HERE'}</span></p>
    </body>
    </html>
  `);
});

// Sample vulnerable endpoint that would return CSS but serve HTML content
app.get('/account/settings/nonexistent.css', (req, res) => {
  // This endpoint would previously be cached by CDN due to .css extension
  // Now it will have proper headers preventing caching
  res.type('css'); // This would be the vulnerability - serving HTML as CSS
  res.send(`
    body { background: red; }
    /* Session token would be here in a real vulnerability */
  `);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});