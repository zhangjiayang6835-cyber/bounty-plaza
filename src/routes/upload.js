const express = require('express');
const multer = require('multer');
const path = require('path');
const { extractZip } = require('../utils/extractZip');
const fs = require('fs');

const router = express.Router();

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = path.join(__dirname, '../../uploads');
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir, { recursive: true });
    }
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    // Generate unique filename to prevent overwrites
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, file.fieldname + '-' + uniqueSuffix + path.extname(file.originalname));
  }
});

const upload = multer({ 
  storage: storage,
  fileFilter: (req, file, cb) => {
    // Only allow zip files
    if (file.mimetype === 'application/zip' || 
        file.originalname.toLowerCase().endsWith('.zip')) {
      cb(null, true);
    } else {
      cb(new Error('Only zip files are allowed'), false);
    }
  }
});

// Upload and extract zip file
router.post('/extract', upload.single('zipFile'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    const zipPath = req.file.path;
    const extractDir = path.join(__dirname, '../../extracted-files');
    
    // Extract the zip file safely
    await extractZip(zipPath, extractDir);
    
    // Clean up the uploaded zip file
    fs.unlinkSync(zipPath);
    
    res.json({ 
      message: 'Zip file extracted successfully',
      extractedTo: extractDir
    });
  } catch (error) {
    console.error('Error extracting zip:', error);
    
    // Clean up the uploaded zip file in case of error
    if (req.file && fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }
    
    res.status(400).json({ error: error.message });
  }
});

module.exports = router;