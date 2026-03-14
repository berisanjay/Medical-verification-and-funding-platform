const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const prisma = require('../utils/prisma');
const { verifyAdmin } = require('../middleware/auth');
const { createOTP, verifyOTP } = require('../utils/otp');

// ─────────────────────────────────────────
// ADMIN LOGIN — Step 1: Password + Admin Key
// ─────────────────────────────────────────
router.post('/login', async (req, res) => {
  try {
    const { email, password, admin_secret } = req.body;

    if (!email || !password || !admin_secret) {
      return res.status(400).json({
        success: false,
        error: 'Email, password and admin secret required'
      });
    }

    // Check admin secret key
    if (admin_secret !== process.env.ADMIN_SECRET_KEY) {
      return res.status(403).json({
        success: false,
        error: 'Invalid admin secret key'
      });
    }

    // Find admin user
    const admin = await prisma.user.findUnique({ where: { email } });
    if (!admin || admin.role !== 'ADMIN') {
      return res.status(401).json({
        success: false,
        error: 'Invalid credentials'
      });
    }

    // Check password
    const valid = await bcrypt.compare(password, admin.password_hash);
    if (!valid) {
      return res.status(401).json({
        success: false,
        error: 'Invalid credentials'
      });
    }

    // Send OTP for 2FA
    await createOTP(admin.id, admin.email, 'ADMIN_LOGIN');

    res.json({
      success  : true,
      message  : 'OTP sent to admin email for 2FA verification',
      admin_id : admin.id
    });

  } catch (error) {
    console.error('Admin login error:', error);
    res.status(500).json({ success: false, error: 'Login failed' });
  }
});

// ─────────────────────────────────────────
// ADMIN LOGIN — Step 2: Verify OTP → Get Token
// ─────────────────────────────────────────
router.post('/verify-otp', async (req, res) => {
  try {
    const { admin_id, otp_code } = req.body;

    if (!admin_id || !otp_code) {
      return res.status(400).json({
        success: false,
        error: 'admin_id and otp_code required'
      });
    }

    const result = await verifyOTP(parseInt(admin_id), otp_code, 'ADMIN_LOGIN');
    if (!result.valid) {
      return res.status(400).json({ success: false, error: result.error });
    }

    // Get admin details
    const admin = await prisma.user.findUnique({
      where: { id: parseInt(admin_id) }
    });

    // Generate admin JWT
    const token = jwt.sign(
      { id: admin.id, email: admin.email, role: 'ADMIN' },
      process.env.JWT_ADMIN_SECRET,
      { expiresIn: '8h' }
    );

    // Log admin login
    await prisma.adminAuditLog.create({
      data: {
        admin_id    : admin.id,
        action      : 'ADMIN_LOGIN',
        target_type : 'auth',
        target_id   : admin.id,
        notes       : 'Admin logged in successfully'
      }
    });

    res.json({
      success : true,
      message : 'Admin login successful',
      token,
      admin   : {
        id    : admin.id,
        name  : admin.name,
        email : admin.email,
        role  : admin.role
      }
    });

  } catch (error) {
    console.error('Admin OTP verify error:', error);
    res.status(500).json({ success: false, error: 'OTP verification failed' });
  }
});

// ─────────────────────────────────────────
// CREATE ADMIN — Only existing admin can create new admin
// ─────────────────────────────────────────
router.post('/create-admin', verifyAdmin, async (req, res) => {
  try {
    const { name, email, password } = req.body;

    if (!name || !email || !password) {
      return res.status(400).json({
        success: false,
        error: 'Name, email and password required'
      });
    }

    const existing = await prisma.user.findUnique({ where: { email } });
    if (existing) {
      return res.status(400).json({
        success: false,
        error: 'Email already exists'
      });
    }

    const password_hash = await bcrypt.hash(password, 12);

    const admin = await prisma.user.create({
      data: {
        name,
        email,
        password_hash,
        role         : 'ADMIN',
        otp_verified : true
      }
    });

    // Log action
    await prisma.adminAuditLog.create({
      data: {
        admin_id    : req.admin.id,
        action      : 'CREATE_ADMIN',
        target_type : 'user',
        target_id   : admin.id,
        notes       : `Created admin account for ${email}`
      }
    });

    res.status(201).json({
      success : true,
      message : 'Admin account created',
      admin   : { id: admin.id, name: admin.name, email: admin.email }
    });

  } catch (error) {
    console.error('Create admin error:', error);
    res.status(500).json({ success: false, error: 'Failed to create admin' });
  }
});

// ─────────────────────────────────────────
// DASHBOARD STATS
// ─────────────────────────────────────────
router.get('/dashboard', verifyAdmin, async (req, res) => {
  try {
    const [
      totalCampaigns,
      liveCampaigns,
      pendingVerification,
      verificationNeeded,
      totalDonations,
      totalUsers,
      blacklisted
    ] = await Promise.all([
      prisma.campaign.count(),
      prisma.campaign.count({ where: { status: 'LIVE_CAMPAIGN' } }),
      prisma.campaign.count({ where: { status: 'PENDING' } }),
      prisma.campaign.count({ where: { status: 'VERIFICATION_NEEDED' } }),
      prisma.donation.aggregate({ _sum: { amount: true }, where: { status: 'SUCCESS' } }),
      prisma.user.count({ where: { role: 'PATIENT' } }),
      prisma.blacklist.count()
    ]);

    res.json({
      success: true,
      stats  : {
        total_campaigns      : totalCampaigns,
        live_campaigns       : liveCampaigns,
        pending_verification : pendingVerification,
        verification_needed  : verificationNeeded,
        total_donations      : totalDonations._sum.amount || 0,
        total_patients       : totalUsers,
        blacklisted_count    : blacklisted
      }
    });

  } catch (error) {
    console.error('Dashboard error:', error);
    res.status(500).json({ success: false, error: 'Failed to get dashboard stats' });
  }
});

// ─────────────────────────────────────────
// GET PENDING CASES
// ─────────────────────────────────────────
router.get('/pending', verifyAdmin, async (req, res) => {
  try {
    const campaigns = await prisma.campaign.findMany({
      where  : { status: 'PENDING' },
      include: {
        patient            : { select: { name: true, email: true } },
        verification_records: { orderBy: { verified_at: 'desc' }, take: 1 },
        documents          : true
      },
      orderBy: { created_at: 'desc' }
    });

    res.json({ success: true, campaigns });

  } catch (error) {
    console.error('Get pending error:', error);
    res.status(500).json({ success: false, error: 'Failed to get pending cases' });
  }
});

// ─────────────────────────────────────────
// GET VERIFICATION NEEDED CASES
// ─────────────────────────────────────────
router.get('/verification-needed', verifyAdmin, async (req, res) => {
  try {
    const campaigns = await prisma.campaign.findMany({
      where  : { status: 'VERIFICATION_NEEDED' },
      include: {
        patient            : { select: { name: true, email: true } },
        verification_records: { orderBy: { verified_at: 'desc' }, take: 1 },
        documents          : true
      },
      orderBy: { created_at: 'desc' }
    });

    res.json({ success: true, campaigns });

  } catch (error) {
    console.error('Get verification needed error:', error);
    res.status(500).json({ success: false, error: 'Failed to get cases' });
  }
});

// ─────────────────────────────────────────
// ADMIN VERIFY CAMPAIGN
// ─────────────────────────────────────────
router.put('/campaigns/:id/verify', verifyAdmin, async (req, res) => {
  try {
    const campaignId = parseInt(req.params.id);
    const { notes } = req.body;

    const campaign = await prisma.campaign.findUnique({
      where  : { id: campaignId },
      include: { patient: true }
    });

    if (!campaign) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    // Update campaign status to VERIFIED
    await prisma.campaign.update({
      where: { id: campaignId },
      data : { status: 'VERIFIED' }
    });

    // Update verification record
    await prisma.verificationRecord.updateMany({
      where: { campaign_id: campaignId },
      data : { status: 'VERIFIED', admin_notes: notes, verified_by: req.admin.id }
    });

    // Log admin action
    await prisma.adminAuditLog.create({
      data: {
        admin_id    : req.admin.id,
        action      : 'CAMPAIGN_VERIFIED',
        target_type : 'campaign',
        target_id   : campaignId,
        notes       : notes || 'Admin verified campaign'
      }
    });

    // Notify patient via Flask
    const axios = require('axios');
    await axios.post(`${process.env.FLASK_BASE_URL}/notify/verification-status`, {
      to_email       : campaign.patient.email,
      patient_name   : campaign.patient.name,
      status         : 'VERIFIED',
      campaign_title : campaign.title
    }, {
      headers: { 'x-flask-secret': process.env.FLASK_INTERNAL_SECRET }
    }).catch(err => console.log('Notification failed:', err.message));

    res.json({ success: true, message: 'Campaign verified successfully' });

  } catch (error) {
    console.error('Verify campaign error:', error);
    res.status(500).json({ success: false, error: 'Failed to verify campaign' });
  }
});

// ─────────────────────────────────────────
// ADMIN CANCEL CAMPAIGN
// ─────────────────────────────────────────
router.put('/campaigns/:id/cancel', verifyAdmin, async (req, res) => {
  try {
    const campaignId = parseInt(req.params.id);
    const { reason } = req.body;

    if (!reason) {
      return res.status(400).json({ success: false, error: 'Cancellation reason required' });
    }

    const campaign = await prisma.campaign.findUnique({
      where  : { id: campaignId },
      include: { patient: true }
    });

    if (!campaign) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    // Cancel campaign
    await prisma.campaign.update({
      where: { id: campaignId },
      data : { status: 'CANCELLED' }
    });

    // Blacklist patient aadhaar and update user
    if (campaign.patient_aadhaar) {
      await prisma.blacklist.upsert({
        where : { aadhaar_number: campaign.patient_aadhaar },
        update: { reason, blacklisted_by: req.admin.id },
        create: {
          aadhaar_number : campaign.patient_aadhaar,
          reason,
          blacklisted_by : req.admin.id
        }
      });
    }

    // Mark user as blacklisted
    await prisma.user.update({
      where: { id: campaign.patient_id },
      data : { is_blacklisted: true, blacklist_reason: reason }
    });

    // Log admin action
    await prisma.adminAuditLog.create({
      data: {
        admin_id    : req.admin.id,
        action      : 'CAMPAIGN_CANCELLED',
        target_type : 'campaign',
        target_id   : campaignId,
        notes       : reason
      }
    });

    // Notify patient
    const axios = require('axios');
    await axios.post(`${process.env.FLASK_BASE_URL}/notify/verification-status`, {
      to_email       : campaign.patient.email,
      patient_name   : campaign.patient.name,
      status         : 'CANCELLED',
      campaign_title : campaign.title,
      reason
    }, {
      headers: { 'x-flask-secret': process.env.FLASK_INTERNAL_SECRET }
    }).catch(err => console.log('Notification failed:', err.message));

    res.json({ success: true, message: 'Campaign cancelled and patient blacklisted' });

  } catch (error) {
    console.error('Cancel campaign error:', error);
    res.status(500).json({ success: false, error: 'Failed to cancel campaign' });
  }
});

// ─────────────────────────────────────────
// GET AUDIT LOG
// ─────────────────────────────────────────
router.get('/audit-log', verifyAdmin, async (req, res) => {
  try {
    const page  = parseInt(req.query.page  || '1');
    const limit = parseInt(req.query.limit || '20');
    const skip  = (page - 1) * limit;

    const [logs, total] = await Promise.all([
      prisma.adminAuditLog.findMany({
        skip,
        take   : limit,
        include: { admin: { select: { name: true, email: true } } },
        orderBy: { performed_at: 'desc' }
      }),
      prisma.adminAuditLog.count()
    ]);

    res.json({ success: true, logs, total, page, limit });

  } catch (error) {
    console.error('Audit log error:', error);
    res.status(500).json({ success: false, error: 'Failed to get audit log' });
  }
});

// ─────────────────────────────────────────
// SEED FIRST ADMIN — only works if no admin exists
// ─────────────────────────────────────────
router.post('/seed', async (req, res) => {
  try {
    const { secret } = req.body;

    // Must provide seed secret
    if (secret !== process.env.ADMIN_SECRET_KEY) {
      return res.status(403).json({ success: false, error: 'Invalid secret' });
    }

    // Check if admin already exists
    const existing = await prisma.user.findFirst({ where: { role: 'ADMIN' } });
    if (existing) {
      return res.status(400).json({ success: false, error: 'Admin already exists' });
    }

    const password_hash = await bcrypt.hash('Admin@MediTrust2026', 12);

    const admin = await prisma.user.create({
      data: {
        name         : 'MediTrust Admin',
        email        : process.env.EMAIL_USER,
        password_hash,
        role         : 'ADMIN',
        otp_verified : true
      }
    });

    res.status(201).json({
      success  : true,
      message  : 'Admin seeded successfully',
      email    : admin.email,
      password : 'Admin@MediTrust2026',
      note     : 'Please change password after first login'
    });

  } catch (error) {
    console.error('Seed error:', error);
    res.status(500).json({ success: false, error: 'Failed to seed admin' });
  }
});

module.exports = router;