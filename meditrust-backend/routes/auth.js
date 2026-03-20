const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const prisma = require('../utils/prisma');
const { createOTP, verifyOTP } = require('../utils/otp');

// ─────────────────────────────────────────
// REGISTER — Step 1: Create account + send OTP
// ─────────────────────────────────────────
router.post('/register', async (req, res) => {
  try {
    const {
      name, email, password, phone,
      aadhaar_number, native_languages
    } = req.body;

    if (!name || !email || !password) {
      return res.status(400).json({ success: false, error: 'Name, email and password are required' });
    }

    // Check if email already exists
    const existing = await prisma.user.findUnique({ where: { email } });
    if (existing) {
      return res.status(400).json({ success: false, error: 'Email already registered' });
    }

    // Check blacklist
    if (aadhaar_number) {
      const blacklisted = await prisma.blacklist.findUnique({
        where: { aadhaar_number }
      });
      if (blacklisted) {
        return res.status(403).json({
          success: false,
          error: 'This Aadhaar number is blacklisted from creating campaigns'
        });
      }
    }

    // Hash password
    const password_hash = await bcrypt.hash(password, 12);

    // Create user — auto-verified in dev mode (no email OTP needed)
    const user = await prisma.user.create({
      data: {
        name,
        email,
        password_hash,
        phone        : phone || null,
        aadhaar_number: aadhaar_number || null,
        native_languages: native_languages || ['en'],
        role         : 'PATIENT',
        otp_verified : true   // DEV MODE: auto-verified — change to false in production
      }
    });

    // DEV MODE: skip OTP email — just return success
    // In production: await createOTP(user.id, email, 'REGISTRATION');
    res.status(201).json({
      success : true,
      message : 'Account created successfully. You can now login.',
      user_id : user.id,
      email   : user.email
    });

  } catch (error) {
    console.error('Register error:', error);
    res.status(500).json({ success: false, error: 'Registration failed' });
  }
});

// ─────────────────────────────────────────
// VERIFY OTP — Step 2: Verify OTP to activate account
// ─────────────────────────────────────────
router.post('/verify-otp', async (req, res) => {
  try {
    const { user_id, otp_code } = req.body;

    if (!user_id || !otp_code) {
      return res.status(400).json({ success: false, error: 'user_id and otp_code required' });
    }

    const result = await verifyOTP(parseInt(user_id), otp_code, 'REGISTRATION');

    if (!result.valid) {
      return res.status(400).json({ success: false, error: result.error });
    }

    // Mark user as verified
    await prisma.user.update({
      where: { id: parseInt(user_id) },
      data : { otp_verified: true }
    });

    res.json({ success: true, message: 'Email verified successfully. You can now login.' });

  } catch (error) {
    console.error('OTP verify error:', error);
    res.status(500).json({ success: false, error: 'OTP verification failed' });
  }
});

// ─────────────────────────────────────────
// RESEND OTP
// ─────────────────────────────────────────
router.post('/resend-otp', async (req, res) => {
  try {
    const { user_id } = req.body;

    const user = await prisma.user.findUnique({ where: { id: parseInt(user_id) } });
    if (!user) {
      return res.status(404).json({ success: false, error: 'User not found' });
    }

    await createOTP(user.id, user.email, 'REGISTRATION');

    res.json({ success: true, message: 'OTP resent to your email' });

  } catch (error) {
    console.error('Resend OTP error:', error);
    res.status(500).json({ success: false, error: 'Failed to resend OTP' });
  }
});

// ─────────────────────────────────────────
// LOGIN — Email + Password only
// ─────────────────────────────────────────
router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ success: false, error: 'Email and password required' });
    }

    // Find user
    const user = await prisma.user.findUnique({ where: { email } });
    if (!user) {
      return res.status(401).json({ success: false, error: 'Invalid email or password' });
    }

    // Check blacklist
    if (user.is_blacklisted) {
      return res.status(403).json({ success: false, error: 'Your account has been suspended' });
    }

    // DEV MODE: otp_verified check disabled — re-enable in production
    // if (!user.otp_verified) {
    //   return res.status(401).json({
    //     success : false,
    //     error   : 'Please verify your email first',
    //     user_id : user.id
    //   });
    // }

    // Check password
    const valid = await bcrypt.compare(password, user.password_hash);
    if (!valid) {
      return res.status(401).json({ success: false, error: 'Invalid email or password' });
    }

    // Generate JWT
    const token = jwt.sign(
      { id: user.id, email: user.email, role: user.role },
      process.env.JWT_SECRET,
      { expiresIn: '7d' }
    );

    res.json({
      success : true,
      message : 'Login successful',
      token,
      user    : {
        id    : user.id,
        name  : user.name,
        email : user.email,
        role  : user.role
      }
    });

  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ success: false, error: 'Login failed' });
  }
});

// ─────────────────────────────────────────
// GET PROFILE
// ─────────────────────────────────────────
router.get('/me', async (req, res) => {
  try {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
      return res.status(401).json({ success: false, error: 'Token required' });
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    const user = await prisma.user.findUnique({
      where : { id: decoded.id },
      select: {
        id               : true,
        name             : true,
        email            : true,
        phone            : true,
        role             : true,
        native_languages : true,
        otp_verified     : true,
        created_at       : true
      }
    });

    if (!user) {
      return res.status(404).json({ success: false, error: 'User not found' });
    }

    res.json({ success: true, user });

  } catch (error) {
    console.error('Get profile error:', error);
    res.status(500).json({ success: false, error: 'Failed to get profile' });
  }
});

module.exports = router;