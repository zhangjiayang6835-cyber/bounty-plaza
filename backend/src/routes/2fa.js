<content>
const express = require('express');
const QRCode = require('qrcode');
const auth = require('../middleware/auth');
const auditLogger = require('../utils/auditLogger');
const User = require('../models/User');

const router = express.Router();

// Generate TOTP QR code
router.post('/generate-qr', auth, async (req, res) => {
  try {
    const user = await User.findById(req.user.id);
    
    if (!user) {
      return res.status(404).json({ message: 'User not found' });
    }
    
    // Generate TOTP secret if not exists
    if (!user.totpSecret) {
      user.totpSecret = generateTOTPSecret();
      await user.save();
    }
    
    // Create otpauth URL
    const otpauthUrl = `otpauth://totp/BountyPlaza:${user.email}?secret=${user.totpSecret}&issuer=BountyPlaza`;
    
    // Generate QR code
    const qrCode = await QRCode.toDataURL(otpauthUrl);
    
    // Log to audit log without sensitive data
    auditLogger.log('2fa_setup', {
      userId: user.id,
      action: 'qr_generated',
      timestamp: new Date().toISOString()
    });
    
    // Return QR code without the secret in the URL
    res.json({
      qrCode,
      message: 'QR code generated successfully'
    });
    
  } catch (error) {
    console.error('Error generating QR code:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Verify TOTP
router.post('/verify', auth, async (req, res) => {
  try {
    const { token } = req.body;
    const user = await User.findById(req.user.id);
    
    if (!user || !user.totpSecret) {
      return res.status(400).json({ message: 'TOTP not set up' });
    }
    
    const isValid = verifyTOTP(token, user.totpSecret);
    
    if (isValid) {
      user.totpEnabled = true;
      await user.save();
      
      auditLogger.log('2fa_setup', {
        userId: user.id,
        action: 'verified',
        timestamp: new Date().toISOString()
      });
      
      res.json({ message: 'TOTP verified successfully' });
    } else {
      auditLogger.log('2fa_setup', {
        userId: user.id,
        action: 'verification_failed',
        timestamp: new Date().toISOString()
      });
      
      res.status(400).json({ message: 'Invalid TOTP token' });
    }
    
  } catch (error) {
    console.error('Error verifying TOTP:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Disable TOTP
router.post('/disable', auth, async (req, res) => {
  try {
    const { password } = req.body;
    const user = await User.findById(req.user.id);
    
    if (!user) {
      return res.status(404).json({ message: 'User not found' });
    }
    
    // Verify password
    const isPasswordValid = await user.comparePassword(password);
    if (!isPasswordValid) {
      auditLogger.log('2fa_setup', {
        userId: user.id,
        action: 'disable_failed',
        reason: 'invalid_password',
        timestamp: new Date().toISOString()
      });
      return res.status(400).json({ message: 'Invalid password' });
    }
    
    user.totpEnabled = false;
    user.totpSecret = null;
    await user.save();
    
    auditLogger.log('2fa_setup', {
      userId: user.id,
      action: 'disabled',
      timestamp: new Date().toISOString()
    });
    
    res.json({ message: 'TOTP disabled successfully' });
    
  } catch (error) {
    console.error('Error disabling TOTP:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

function generateTOTPSecret() {
  // Generate a random base32 secret
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let secret = '';
  for (let i = 0; i < 32; i++) {
    secret += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return secret;
}

function verifyTOTP(token, secret) {
  // Implementation of TOTP verification
  // This is a simplified version - in production you'd use a library like speakeasy
  const crypto = require('crypto');
  const epoch = Math.floor(Date.now() / 30000);
  const hmac = crypto.createHmac('sha1', secret);
  hmac.update(Buffer.from(epoch.toString(), 'hex'));
  const digest = hmac.digest('hex');
  const offset = parseInt(digest.slice(-1), 16);
  const binary = parseInt(digest.slice(offset * 2, offset * 2 + 8), 16);
  const otp = (binary & 0x7fffffff).toString().slice(-6);
  return otp === token;
}

module.exports = router;