const express = require('express');
const axios = require('axios');
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

    // Generate token directly without OTP
    const token = jwt.sign(
      { id: admin.id, email: admin.email, role: 'ADMIN' },
      process.env.JWT_ADMIN_SECRET,
      { expiresIn: '8h' }
    );

    res.json({
      success: true,
      token,
      admin: { id: admin.id, name: admin.name, email: admin.email }
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

    // OTP DISABLED FOR DEVELOPMENT — re-enable before production
    // const result = await verifyOTP(parseInt(admin_id), otp_code, 'ADMIN_LOGIN');
    // if (!result.valid) {
    //   return res.status(400).json({ success: false, error: result.error });
    // }

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
      prisma.campaign.count({ where: { status: { in: ['PENDING', 'PENDING_VERIFICATION', 'VERIFIED', 'VERIFICATION_NEEDED'] } } }),
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
// GET CAMPAIGN FULL REVIEW (Admin)
// Returns patient details + documents + HMS check
// ─────────────────────────────────────────
router.get('/campaigns/:id/review', verifyAdmin, async (req, res) => {
  try {
    const campaignId = parseInt(req.params.id);

    // ── 1. Get campaign + patient details ──
    const campaign = await prisma.campaign.findUnique({
      where  : { id: campaignId },
      include: {
        patient             : { select: { email: true, phone: true, created_at: true } },
        documents           : true,
        verification_records: { orderBy: { verified_at: 'desc' }, take: 1 }
      }
    });

    if (!campaign) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    // ── 2. HMS Verification ──────────────────
    let hmsResult = {
      found           : false,
      name_match      : false,
      aadhaar_match   : false,
      amount_match    : false,
      payment_status  : null,
      hms_patient     : null,
      error           : null
    };

    try {
      // Search HMS by Aadhaar number
      const hmsRes = await axios.get(
        `${process.env.HMS_BASE_URL}/hms/patients/search`,
        {
          params: { aadhaar: campaign.patient_aadhaar },
          timeout: 5000
        }
      );

      if (hmsRes.data.success && hmsRes.data.patients?.length > 0) {
        const hmsPatient = hmsRes.data.patients[0];
        hmsResult.found        = true;
        hmsResult.hms_patient  = hmsPatient;

        // Compare name (case insensitive, partial match)
        const campaignName = campaign.patient_full_name.toLowerCase().trim();
        const hmsName      = hmsPatient.patient_name?.toLowerCase().trim() || '';
        hmsResult.name_match = (
          hmsName.includes(campaignName.split(' ')[0].toLowerCase()) ||
          campaignName.includes(hmsName.split(' ')[0].toLowerCase())
        );

        // Compare Aadhaar
        hmsResult.aadhaar_match = (
          hmsPatient.aadhaar_number?.replace(/\s/g, '') ===
          campaign.patient_aadhaar?.replace(/\s/g, '')
        );

        // Compare amount (within 20% tolerance)
        const campaignAmount = parseFloat(campaign.verified_amount || 0);
        const hmsEstimate    = parseFloat(hmsPatient.ledger?.total_estimate || 0);
        if (campaignAmount > 0 && hmsEstimate > 0) {
          const diff = Math.abs(campaignAmount - hmsEstimate);
          hmsResult.amount_match = (diff / hmsEstimate) <= 0.20;
          hmsResult.hms_amount   = hmsEstimate;
        }

        // Payment status from HMS ledger
        hmsResult.payment_status = {
          total_estimate  : hmsPatient.ledger?.total_estimate   || 0,
          amount_paid     : hmsPatient.ledger?.amount_paid      || 0,
          outstanding     : hmsPatient.ledger?.outstanding_amount || 0,
        };

        hmsResult.patient_status = hmsPatient.status;
      }
    } catch (hmsErr) {
      hmsResult.error = 'HMS server unavailable: ' + hmsErr.message;
      console.log('HMS check failed:', hmsErr.message);
    }

    // ── 3. Verification record ───────────────
    const verRecord = campaign.verification_records[0] || {};

    // ── 4. Build response ────────────────────
    res.json({
      success : true,
      campaign: {
        id                       : campaign.id,
        title                    : campaign.title,
        status                   : campaign.status,
        created_at               : campaign.created_at,
        verified_amount          : campaign.verified_amount,
        relationship_to_fundraiser: campaign.relationship_to_fundraiser,
      },
      patient: {
        full_name   : campaign.patient_full_name,
        age         : campaign.patient_age,
        gender      : campaign.patient_gender,
        aadhaar     : campaign.patient_aadhaar,
        city        : campaign.patient_city,
        state       : campaign.patient_state,
        languages   : campaign.patient_languages,
        email       : campaign.patient?.email,
        phone       : campaign.patient?.phone,
      },
      documents: campaign.documents.map(doc => ({
        id           : doc.id,
        document_type: doc.document_type,
        file_name    : doc.file_name,
        created_at   : doc.created_at,
      })),
      ai_verification: {
        status        : verRecord.status,
        risk_score    : verRecord.risk_score,
        extracted_data: verRecord.extracted_data,
        issues        : verRecord.issues,
        has_tampering : verRecord.has_tampering,
        has_expired   : verRecord.has_expired,
        verified_at   : verRecord.verified_at,
      },
      hms: hmsResult
    });

  } catch (error) {
    console.error('Campaign review error:', error);
    res.status(500).json({ success: false, error: 'Failed to get campaign review' });
  }
});

// ─────────────────────────────────────────
// GET PENDING CASES
// ─────────────────────────────────────────
router.get('/pending', verifyAdmin, async (req, res) => {
  try {
    const campaigns = await prisma.campaign.findMany({
      where  : { status: { in: ['PENDING', 'PENDING_VERIFICATION', 'VERIFICATION_NEEDED', 'VERIFIED'] } },
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

    // Generate UPI ID and QR code
    const { v4: uuidv4 } = require('uuid');
    const QRCode          = require('qrcode');

    const publicUrl  = `meditrust.in/campaign/${uuidv4().split('-')[0]}`;
    const upiId      = `meditrust.${campaignId}@ybl`;
    const qrCodeUrl  = await QRCode.toDataURL(
      `upi://pay?pa=${upiId}&pn=MediTrust&tn=Campaign-${campaignId}`
    );
    const expiresAt  = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000);

    // Update campaign → LIVE directly
    await prisma.campaign.update({
      where: { id: campaignId },
      data : {
        status      : 'LIVE_CAMPAIGN',
        story_approved: true,
        public_url  : publicUrl,
        upi_id      : upiId,
        qr_code_url : qrCodeUrl,
        expires_at  : expiresAt
      }
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
        notes       : notes || 'Admin approved — campaign now LIVE'
      }
    });

    // Send campaign LIVE email to patient
    await axios.post(`${process.env.FLASK_BASE_URL}/notify/campaign-live`, {
      to_email       : campaign.patient.email,
      patient_name   : campaign.patient_full_name,
      campaign_title : campaign.title,
      public_url     : publicUrl,
      upi_id         : upiId
    }, {
      headers: { 'x-flask-secret': process.env.FLASK_INTERNAL_SECRET }
    }).catch(err => console.log('Live notification failed:', err.message));

    res.json({
      success   : true,
      message   : 'Campaign approved and is now LIVE!',
      public_url: publicUrl,
      upi_id    : upiId
    });

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

    // ── Send rejection email BEFORE deleting data ──────────────
    await axios.post(`${process.env.FLASK_BASE_URL}/notify/campaign-rejected`, {
      to_email       : campaign.patient.email,
      patient_name   : campaign.patient_full_name,
      campaign_title : campaign.title,
      reason
    }, {
      headers: { 'x-flask-secret': process.env.FLASK_INTERNAL_SECRET }
    }).catch(err => console.log('Rejection email failed:', err.message));

    // ── Delete all campaign data from DB ─────────────────────────
    // Order matters — delete children before parent
    await prisma.verificationRecord.deleteMany({ where: { campaign_id: campaignId } });
    await prisma.campaignDocument.deleteMany({  where: { campaign_id: campaignId } });
    await prisma.campaignUpdate.deleteMany({    where: { campaign_id: campaignId } });
    await prisma.nGOMatch.deleteMany({          where: { campaign_id: campaignId } });
    await prisma.fundRelease.deleteMany({       where: { campaign_id: campaignId } });
    await prisma.donation.deleteMany({          where: { campaign_id: campaignId } });

    // Delete FundNeeder if exists
    try {
      await prisma.fundNeeder.delete({ where: { campaign_id: campaignId } });
    } catch(e) { /* may not exist */ }

    // Delete campaign itself
    await prisma.campaign.delete({ where: { id: campaignId } });
    console.log(`✅ Campaign ${campaignId} deleted from DB`);

    // Blacklist aadhaar only if fraud detected
    const isFraud = reason.toLowerCase().includes('fraud') ||
                    reason.toLowerCase().includes('fake') ||
                    reason.toLowerCase().includes('tamper');

    if (isFraud && campaign.patient_aadhaar) {
      await prisma.blacklist.upsert({
        where : { aadhaar_number: campaign.patient_aadhaar },
        update: { reason, blacklisted_by: req.admin.id },
        create: {
          aadhaar_number : campaign.patient_aadhaar,
          reason,
          blacklisted_by : req.admin.id
        }
      });
      await prisma.user.update({
        where: { id: campaign.patient_id },
        data : { is_blacklisted: true, blacklist_reason: reason }
      });
      console.log(`🚫 Patient blacklisted for fraud: ${campaign.patient_aadhaar}`);
    }

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

    res.json({
      success : true,
      message : 'Campaign rejected, data deleted, patient notified by email',
      fraud_blacklisted: isFraud
    });

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

// ─────────────────────────────────────────
// GET SINGLE DOCUMENT CONTENT (base64) — Admin viewing
// ─────────────────────────────────────────
router.get('/documents/:id', verifyAdmin, async (req, res) => {
  try {
    const doc = await prisma.campaignDocument.findUnique({
      where: { id: parseInt(req.params.id) }
    });
    if (!doc) return res.status(404).json({ success: false, error: 'Document not found' });

    // file_url is stored as base64 data URL: "data:application/pdf;base64,..."
    const fileUrl = doc.file_url || '';

    if (fileUrl.startsWith('data:')) {
      // Extract mime type and base64 data
      const matches = fileUrl.match(/^data:([^;]+);base64,(.+)$/);
      if (matches) {
        const mimeType = matches[1];
        const base64Data = matches[2];
        
        // Return base64 data directly for frontend to handle
        return res.json({
          success: true,
          document_data: base64Data,
          file_name: doc.file_name,
          document_type: doc.document_type,
          mime_type: mimeType
        });
      }
    }

    // Fallback — return error if not base64
    res.status(400).json({ success: false, error: 'Document data not found' });

  } catch (error) {
    console.error('Get document error:', error);
    res.status(500).json({ success: false, error: 'Failed to get document' });
  }
});

// ─────────────────────────────────────────
// GET ALL CAMPAIGNS — Admin (all statuses)
// ─────────────────────────────────────────
router.get('/campaigns', verifyAdmin, async (req, res) => {
  try {
    const { status, page = 1, limit = 20 } = req.query;
    const skip = (parseInt(page) - 1) * parseInt(limit);

    const where = status ? { status } : {};

    const [campaigns, total] = await Promise.all([
      prisma.campaign.findMany({
        where,
        skip,
        take   : parseInt(limit),
        include: {
          patient            : { select: { name: true, email: true, phone: true } },
          verification_records: { orderBy: { verified_at: 'desc' }, take: 1 }
        },
        orderBy: { created_at: 'desc' }
      }),
      prisma.campaign.count({ where })
    ]);

    res.json({ success: true, campaigns, total, page: parseInt(page), limit: parseInt(limit) });

  } catch (error) {
    console.error('Get all campaigns error:', error);
    res.status(500).json({ success: false, error: 'Failed to get campaigns' });
  }
});

// ─────────────────────────────────────────
// GET BLACKLIST — Admin
// ─────────────────────────────────────────
router.get('/blacklist', verifyAdmin, async (req, res) => {
  try {
    const blacklist = await prisma.blacklist.findMany({
      orderBy: { blacklisted_at: 'desc' }
    });

    res.status(201).json({
      success  : true,
      message  : 'Admin seeded successfully',
      email    : admin.email,
      password : 'Admin@MediTrust2026',
      note     : 'Please change password after first login'
    });

  } catch (error) {
    console.error('Get blacklist error:', error);
    res.status(500).json({ success: false, error: 'Failed to get blacklist' });
  }
});

// ─────────────────────────────────────────
// GET MY CAMPAIGNS (Patient)
// ─────────────────────────────────────────
router.get('/my/campaigns', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    if (!token) {
      return res.status(401).json({ success: false, error: 'Token required' });
    }

    // Verify token
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    const user = await prisma.user.findUnique({ where: { id: decoded.userId } });
    if (!user || user.role !== 'PATIENT') {
      return res.status(403).json({ success: false, error: 'Patient access required' });
    }

    // Get user's campaigns
    const campaigns = await prisma.campaign.findMany({
      where: { patient_id: user.id },
      include: {
        hospital: { select: { name: true, city: true } }
      },
      orderBy: { created_at: 'desc' }
    });

    res.json({
      success: true,
      campaigns: campaigns.map(c => ({
        id: c.id,
        title: c.title,
        status: c.status,
        created_at: c.created_at,
        expires_at: c.expires_at,
        verified_amount: c.verified_amount,
        collected_amount: c.collected_amount,
        released_amount: c.released_amount,
        patient_full_name: c.patient_full_name,
        public_url: c.public_url,
        upi_id: c.upi_id,
        qr_code_url: c.qr_code_url,
        hospital: c.hospital
      }))
    });

  } catch (error) {
    console.error('Get my campaigns error:', error);
    if (error.name === 'JsonWebTokenError') {
      return res.status(401).json({ success: false, error: 'Invalid token' });
    }
    res.status(500).json({ success: false, error: 'Failed to get campaigns' });
  }
});

module.exports = router;