/**
 * MediTrust — Internal Routes
 * Called ONLY by Flask FulfillmentManager background thread
 * Protected by x-flask-secret header
 * Never exposed to public or patients
 */

const express = require('express');
const router  = express.Router();
const prisma  = require('../utils/prisma');
const { verifyFlaskSecret } = require('../middleware/auth');

// ─────────────────────────────────────────
// CHECK 1 — Find campaigns where outstanding = 0
// GET /internal/campaigns/check-completed
// ─────────────────────────────────────────
router.get('/campaigns/check-completed', verifyFlaskSecret, async (req, res) => {
  try {
    // Find LIVE campaigns that are fully funded
    const campaigns = await prisma.campaign.findMany({
      where: {
        status: 'LIVE_CAMPAIGN',
        verified_amount: { not: null },
      },
      include: {
        patient : { select: { email: true, name: true } },
        donations: { where: { status: 'SUCCESS' }, select: { donor_name: true, donor_email: true, is_anonymous: true, amount: true } }
      }
    });

    // Filter: collected >= verified (fully funded)
    const completed = campaigns
      .filter(c => parseFloat(c.collected_amount) >= parseFloat(c.verified_amount))
      .map(c => ({
        id             : c.id,
        title          : c.title,
        patient_email  : c.patient?.email,
        patient_name   : c.patient?.name,
        collected_amount: c.collected_amount,
        public_url     : c.public_url,
        upi_id         : c.upi_id,
        donors         : c.donations
          .filter(d => !d.is_anonymous && d.donor_email)
          .map(d => ({ name: d.donor_name, email: d.donor_email, amount: d.amount }))
      }));

    res.json({ success: true, completed_campaigns: completed });

  } catch (error) {
    console.error('check-completed error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// CHECK 2 — Find campaigns past expiry date
// GET /internal/campaigns/check-expired
// ─────────────────────────────────────────
router.get('/campaigns/check-expired', verifyFlaskSecret, async (req, res) => {
  try {
    const now = new Date();

    const expired = await prisma.campaign.findMany({
      where: {
        status    : 'LIVE_CAMPAIGN',
        expires_at: { lt: now }
      },
      select: { id: true, title: true }
    });

    res.json({
      success           : true,
      expired_campaigns : expired.map(c => ({ id: c.id, title: c.title }))
    });

  } catch (error) {
    console.error('check-expired error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// CHECK 3 — Find LIVE campaigns with expired documents
// GET /internal/campaigns/check-document-expiry
// ─────────────────────────────────────────
router.get('/campaigns/check-document-expiry', verifyFlaskSecret, async (req, res) => {
  try {
    // Find campaigns with UPDATE_NEEDED verification status
    // that are still showing as LIVE (not yet blocked)
    const campaigns = await prisma.campaign.findMany({
      where : { status: 'LIVE_CAMPAIGN' },
      include: {
        patient             : { select: { email: true, name: true } },
        verification_records: {
          where  : { has_expired: true },
          orderBy: { verified_at: 'desc' },
          take   : 1
        }
      }
    });

    const needUpdate = campaigns
      .filter(c => c.verification_records.length > 0)
      .map(c => ({
        id            : c.id,
        title         : c.title,
        patient_email : c.patient?.email,
        patient_name  : c.patient?.name,
      }));

    res.json({ success: true, update_needed_campaigns: needUpdate });

  } catch (error) {
    console.error('check-document-expiry error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// CHECK 4 — Get pending fund releases
// GET /internal/releases/pending
// ─────────────────────────────────────────
router.get('/releases/pending', verifyFlaskSecret, async (req, res) => {
  try {
    const releases = await prisma.fundRelease.findMany({
      where  : { status: 'PENDING' },
      include: {
        campaign: {
          include: {
            patient : { select: { email: true, name: true } },
            hospital: true
          }
        }
      }
    });

    const result = releases.map(r => ({
      id            : r.id,
      campaign_id   : r.campaign_id,
      amount        : r.amount,
      patient_hms_id: r.campaign.patient_hms_id,
      patient_email : r.campaign.patient?.email,
      patient_name  : r.campaign.patient?.name,
      campaign_title: r.campaign.title,
    }));

    res.json({ success: true, pending_releases: result });

  } catch (error) {
    console.error('pending releases error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// MARK campaign COMPLETED
// POST /internal/campaigns/:id/complete
// ─────────────────────────────────────────
router.post('/campaigns/:id/complete', verifyFlaskSecret, async (req, res) => {
  try {
    await prisma.campaign.update({
      where: { id: parseInt(req.params.id) },
      data : { status: 'COMPLETED' }
    });
    res.json({ success: true, message: 'Campaign marked COMPLETED' });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// MARK campaign EXPIRED
// POST /internal/campaigns/:id/expire
// ─────────────────────────────────────────
router.post('/campaigns/:id/expire', verifyFlaskSecret, async (req, res) => {
  try {
    await prisma.campaign.update({
      where: { id: parseInt(req.params.id) },
      data : { status: 'EXPIRED' }
    });
    res.json({ success: true, message: 'Campaign marked EXPIRED' });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// MARK campaign UPDATE_NEEDED
// POST /internal/campaigns/:id/update-needed
// ─────────────────────────────────────────
router.post('/campaigns/:id/update-needed', verifyFlaskSecret, async (req, res) => {
  try {
    await prisma.campaign.update({
      where: { id: parseInt(req.params.id) },
      data : { status: 'UPDATE_NEEDED' }
    });
    res.json({ success: true, message: 'Campaign marked UPDATE_NEEDED' });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// VERIFY hospital is still correct
// GET /internal/campaigns/:id/verify-hospital
// ─────────────────────────────────────────
router.get('/campaigns/:id/verify-hospital', verifyFlaskSecret, async (req, res) => {
  try {
    const campaign = await prisma.campaign.findUnique({
      where  : { id: parseInt(req.params.id) },
      include: { verification_records: { orderBy: { verified_at: 'desc' }, take: 1 } }
    });

    if (!campaign) {
      return res.status(404).json({ success: false, hospital_verified: false });
    }

    const latestVerification = campaign.verification_records[0];
    const hospitalVerified   = latestVerification?.status === 'VERIFIED';

    res.json({
      success         : true,
      hospital_verified: hospitalVerified,
      campaign_status  : campaign.status,
      hospital_id      : campaign.hospital_id
    });

  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// APPROVE a fund release
// POST /internal/releases/:id/approve
// ─────────────────────────────────────────
router.post('/releases/:id/approve', verifyFlaskSecret, async (req, res) => {
  try {
    const { amount } = req.body;

    const release = await prisma.fundRelease.update({
      where: { id: parseInt(req.params.id) },
      data : { status: 'APPROVED' }
    });

    // Update campaign released amount
    await prisma.campaign.update({
      where: { id: release.campaign_id },
      data : { released_amount: { increment: parseFloat(amount) } }
    });

    res.json({ success: true, release });

  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// BLOCK a fund release
// POST /internal/releases/:id/block
// ─────────────────────────────────────────
router.post('/releases/:id/block', verifyFlaskSecret, async (req, res) => {
  try {
    const { reason } = req.body;

    await prisma.fundRelease.update({
      where: { id: parseInt(req.params.id) },
      data : { status: 'BLOCKED', block_reason: reason }
    });

    res.json({ success: true, message: 'Release blocked: ' + reason });

  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// HEALTH CHECK
// GET /internal
// ─────────────────────────────────────────
router.get('/', (req, res) => {
  res.json({
    message  : 'MediTrust Internal Routes — Active',
    routes   : [
      'GET  /internal/campaigns/check-completed',
      'GET  /internal/campaigns/check-expired',
      'GET  /internal/campaigns/check-document-expiry',
      'GET  /internal/releases/pending',
      'POST /internal/campaigns/:id/complete',
      'POST /internal/campaigns/:id/expire',
      'POST /internal/campaigns/:id/update-needed',
      'GET  /internal/campaigns/:id/verify-hospital',
      'POST /internal/releases/:id/approve',
      'POST /internal/releases/:id/block',
    ]
  });
});

module.exports = router;