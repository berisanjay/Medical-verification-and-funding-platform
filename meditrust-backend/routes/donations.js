const express = require('express');
const router  = express.Router();
const prisma  = require('../utils/prisma');
const axios   = require('axios');
const Razorpay = require('razorpay');
const crypto  = require('crypto');
const { verifyAdmin, verifyToken } = require('../middleware/auth');

// Initialize Razorpay
const razorpay = new Razorpay({
  key_id    : process.env.RAZORPAY_KEY_ID,
  key_secret: process.env.RAZORPAY_KEY_SECRET
});

// ─────────────────────────────────────────
// HELPER — Notify Flask
// ─────────────────────────────────────────
const notifyFlask = async (path, data) => {
  try {
    await axios.post(`${process.env.FLASK_BASE_URL}${path}`, data, {
      headers : { 'x-flask-secret': process.env.FLASK_INTERNAL_SECRET },
      timeout : 8000
    });
  } catch (err) {
    console.log(`Flask notification failed [${path}]:`, err.message);
  }
};

// ─────────────────────────────────────────
// POST /api/donations/initiate
// Initiate donation — Create Razorpay Order
// ─────────────────────────────────────────
router.post('/initiate', async (req, res) => {
  try {
    const { campaign_id, donor_name, donor_email, amount, is_anonymous } = req.body;

    // Validation
    if (!campaign_id || !amount) {
      return res.status(400).json({
        success: false,
        error  : 'campaign_id and amount are required'
      });
    }

    // Anonymous donations don't need a name/email
    const isAnon = is_anonymous === true || is_anonymous === 'true';
    if (!isAnon && (!donor_name || !donor_email)) {
      return res.status(400).json({
        success: false,
        error  : 'donor_name and donor_email are required for non-anonymous donations'
      });
    }

    const parsedAmount = parseFloat(amount);
    if (isNaN(parsedAmount) || parsedAmount < 1) {
      return res.status(400).json({ success: false, error: 'Amount must be at least ₹1' });
    }

    // Check campaign is live
    const campaign = await prisma.campaign.findUnique({
      where: { id: parseInt(campaign_id) }
    });

    if (!campaign) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    if (campaign.status !== 'LIVE_CAMPAIGN') {
      return res.status(400).json({
        success: false,
        error  : 'This campaign is not currently accepting donations'
      });
    }

    // Create Razorpay order
    const order = await razorpay.orders.create({
      amount  : Math.round(parsedAmount * 100), // paise
      currency: 'INR',
      notes   : {
        campaign_id: campaign_id.toString(),
        donor_email : donor_email || 'anonymous',
        donor_name  : donor_name  || 'Anonymous Donor'
      }
    });

    // Create pending donation record
    const donation = await prisma.donation.create({
      data: {
        campaign_id : parseInt(campaign_id),
        donor_name  : isAnon ? 'Anonymous Donor' : donor_name,
        donor_email : isAnon ? 'anonymous@meditrust.in' : donor_email,
        is_anonymous: isAnon,
        amount      : parsedAmount,
        order_id    : order.id,
        status      : 'PENDING'
      }
    });

    res.json({
      success     : true,
      order_id    : order.id,
      donation_id : donation.id,
      amount      : order.amount,    // in paise
      currency    : order.currency,
      key_id      : process.env.RAZORPAY_KEY_ID,
      campaign    : {
        title      : campaign.title,
        hospital   : campaign.patient_city || ''
      }
    });

  } catch (error) {
    console.error('Initiate donation error:', error);
    res.status(500).json({ success: false, error: 'Failed to initiate donation' });
  }
});

// ─────────────────────────────────────────
// POST /api/donations/verify
// Verify payment after Razorpay callback
// ─────────────────────────────────────────
router.post('/verify', async (req, res) => {
  try {
    const {
      donation_id,
      razorpay_order_id,
      razorpay_payment_id,
      razorpay_signature
    } = req.body;

    if (!donation_id || !razorpay_order_id || !razorpay_payment_id || !razorpay_signature) {
      return res.status(400).json({
        success: false,
        error  : 'donation_id, razorpay_order_id, razorpay_payment_id and razorpay_signature are required'
      });
    }

    // Verify Razorpay signature
    const body     = razorpay_order_id + '|' + razorpay_payment_id;
    const expected = crypto
      .createHmac('sha256', process.env.RAZORPAY_KEY_SECRET)
      .update(body)
      .digest('hex');

    if (expected !== razorpay_signature) {
      // Mark donation as failed
      await prisma.donation.update({
        where: { id: parseInt(donation_id) },
        data : { status: 'FAILED' }
      }).catch(() => {});

      return res.status(400).json({
        success: false,
        error  : 'Payment verification failed — invalid signature'
      });
    }

    // Check donation exists and is still pending
    const existing = await prisma.donation.findUnique({
      where: { id: parseInt(donation_id) }
    });

    if (!existing) {
      return res.status(404).json({ success: false, error: 'Donation record not found' });
    }

    if (existing.status === 'SUCCESS') {
      // Already verified — idempotent response
      return res.json({
        success     : true,
        message     : 'Payment already verified',
        donation_id : existing.id,
        receipt_sent: existing.receipt_sent
      });
    }

    // Update donation to SUCCESS
    const donation = await prisma.donation.update({
      where: { id: parseInt(donation_id) },
      data : {
        status    : 'SUCCESS',
        payment_id: razorpay_payment_id
      }
    });

    // Update campaign collected amount
    await prisma.campaign.update({
      where: { id: donation.campaign_id },
      data : { collected_amount: { increment: donation.amount } }
    });

    // Get fresh campaign details
    const campaign = await prisma.campaign.findUnique({
      where  : { id: donation.campaign_id },
      include: { patient: { select: { name: true, email: true, native_languages: true } } }
    });

    // Send receipt email via Flask (only non-anonymous donors)
    if (!donation.is_anonymous && donation.donor_email !== 'anonymous@meditrust.in') {
      try {
        await notifyFlask('/notify/donation-receipt', {
          to_email      : donation.donor_email,
          donor_name    : donation.donor_name,
          campaign_title: campaign.title,
          amount        : parseFloat(donation.amount),
          transaction_id: razorpay_payment_id,
          donated_at    : donation.donated_at,
          campaign_url  : `${process.env.FRONTEND_URL || 'http://localhost:3000'}/campaign.html?id=${campaign.id}`
        });

        await prisma.donation.update({
          where: { id: donation.id },
          data : { receipt_sent: true }
        });
      } catch (e) {
        console.log('Receipt email failed:', e.message);
      }
    }

    // Check if campaign is fully funded
    const updatedCampaign = await prisma.campaign.findUnique({
      where: { id: donation.campaign_id }
    });

    if (
      updatedCampaign.verified_amount &&
      parseFloat(updatedCampaign.collected_amount) >= parseFloat(updatedCampaign.verified_amount)
    ) {
      await prisma.campaign.update({
        where: { id: donation.campaign_id },
        data : { status: 'COMPLETED' }
      });

      // Notify patient that goal is reached
      if (campaign.patient?.email) {
        await notifyFlask('/notify/campaign-completed', {
          to_email       : campaign.patient.email,
          patient_name   : campaign.patient.name,
          campaign_title : campaign.title,
          total_collected: parseFloat(updatedCampaign.collected_amount)
        });
      }
    }

    res.json({
      success     : true,
      message     : 'Payment verified successfully',
      donation_id : donation.id,
      receipt_sent: !donation.is_anonymous,
      campaign    : {
        id             : campaign.id,
        collected_amount: parseFloat(updatedCampaign.collected_amount),
        verified_amount : parseFloat(updatedCampaign.verified_amount || 0),
        status         : updatedCampaign.status
      }
    });

  } catch (error) {
    console.error('Verify donation error:', error);
    res.status(500).json({ success: false, error: 'Payment verification failed' });
  }
});

// ─────────────────────────────────────────
// GET /api/donations/campaign/:campaign_id
// Get all successful donations for a campaign (public)
// ─────────────────────────────────────────
router.get('/campaign/:campaign_id', async (req, res) => {
  try {
    const campaignId = parseInt(req.params.campaign_id);
    if (isNaN(campaignId)) {
      return res.status(400).json({ success: false, error: 'Invalid campaign ID' });
    }

    const page  = parseInt(req.query.page  || '1');
    const limit = parseInt(req.query.limit || '20');
    const skip  = (page - 1) * limit;

    const [donations, total] = await Promise.all([
      prisma.donation.findMany({
        where  : { campaign_id: campaignId, status: 'SUCCESS' },
        select : {
          donor_name  : true,
          is_anonymous: true,
          amount      : true,
          donated_at  : true
        },
        orderBy: { donated_at: 'desc' },
        skip,
        take: limit
      }),
      prisma.donation.count({
        where: { campaign_id: campaignId, status: 'SUCCESS' }
      })
    ]);

    // Mask anonymous donor names
    const cleaned = donations.map(d => ({
      ...d,
      donor_name: d.is_anonymous ? 'Anonymous Donor' : d.donor_name,
      amount    : parseFloat(d.amount)
    }));

    res.json({
      success  : true,
      donations: cleaned,
      total,
      page,
      limit
    });

  } catch (error) {
    console.error('Get donations error:', error);
    res.status(500).json({ success: false, error: 'Failed to get donations' });
  }
});

// ─────────────────────────────────────────
// GET /api/donations/stats/:campaign_id
// Get donation stats for analytics dashboard
// ─────────────────────────────────────────
router.get('/stats/:campaign_id', async (req, res) => {
  try {
    const campaignId = parseInt(req.params.campaign_id);
    if (isNaN(campaignId)) {
      return res.status(400).json({ success: false, error: 'Invalid campaign ID' });
    }

    const [campaign, donationStats, recentDonations] = await Promise.all([
      prisma.campaign.findUnique({
        where : { id: campaignId },
        select: { verified_amount: true, collected_amount: true, status: true }
      }),
      prisma.donation.aggregate({
        where  : { campaign_id: campaignId, status: 'SUCCESS' },
        _count : { id: true },
        _sum   : { amount: true },
        _avg   : { amount: true },
        _max   : { amount: true }
      }),
      prisma.donation.findMany({
        where  : { campaign_id: campaignId, status: 'SUCCESS' },
        select : {
          donor_name  : true,
          is_anonymous: true,
          amount      : true,
          donated_at  : true
        },
        orderBy: { donated_at: 'desc' },
        take   : 5
      })
    ]);

    if (!campaign) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    const totalDonors    = donationStats._count.id;
    const totalCollected = parseFloat(donationStats._sum.amount || 0);
    const avgDonation    = parseFloat(donationStats._avg.amount || 0);
    const maxDonation    = parseFloat(donationStats._max.amount || 0);
    const verifiedAmount = parseFloat(campaign.verified_amount || 0);
    const progressPct    = verifiedAmount > 0
      ? Math.min(100, Math.round((totalCollected / verifiedAmount) * 100))
      : 0;

    res.json({
      success : true,
      stats   : {
        total_donors    : totalDonors,
        total_collected : totalCollected,
        verified_amount : verifiedAmount,
        progress_percent: progressPct,
        avg_donation    : Math.round(avgDonation),
        max_donation    : maxDonation,
        campaign_status : campaign.status
      },
      recent_donations: recentDonations.map(d => ({
        ...d,
        donor_name: d.is_anonymous ? 'Anonymous Donor' : d.donor_name,
        amount    : parseFloat(d.amount)
      }))
    });

  } catch (error) {
    console.error('Donation stats error:', error);
    res.status(500).json({ success: false, error: 'Failed to get donation stats' });
  }
});

// ─────────────────────────────────────────
// GET /api/donations  (Admin — all donations)
// ─────────────────────────────────────────
router.get('/', verifyAdmin, async (req, res) => {
  try {
    const page   = parseInt(req.query.page   || '1');
    const limit  = parseInt(req.query.limit  || '30');
    const status = req.query.status || undefined;
    const skip   = (page - 1) * limit;

    const where = status ? { status } : {};

    const [donations, total] = await Promise.all([
      prisma.donation.findMany({
        where,
        skip,
        take   : limit,
        include: {
          campaign: { select: { id: true, title: true } }
        },
        orderBy: { donated_at: 'desc' }
      }),
      prisma.donation.count({ where })
    ]);

    const cleaned = donations.map(d => ({
      ...d,
      amount    : parseFloat(d.amount),
      donor_name: d.is_anonymous ? 'Anonymous Donor' : d.donor_name
    }));

    res.json({ success: true, donations: cleaned, total, page, limit });

  } catch (error) {
    console.error('Admin get donations error:', error);
    res.status(500).json({ success: false, error: 'Failed to get donations' });
  }
});

// ─────────────────────────────────────────
// POST /api/donations/suggest
// Submit donor comment / hospital suggestion
// Sent to Flask → Gemini + Google Places validation
// ─────────────────────────────────────────
router.post('/suggest', async (req, res) => {
  try {
    const { campaign_id, suggestion_text } = req.body;

    if (!campaign_id || !suggestion_text?.trim()) {
      return res.status(400).json({
        success: false,
        error  : 'campaign_id and suggestion_text are required'
      });
    }

    const campaign = await prisma.campaign.findUnique({
      where  : { id: parseInt(campaign_id) },
      include: {
        patient    : { select: { name: true, email: true, native_languages: true } },
        fund_needer: { select: { disease: true, hospital_name: true } }
      }
    });

    if (!campaign) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    // Get disease from FundNeeder (extracted by AI)
    const diseaseText = campaign.fund_needer?.disease || '';

    // Send to Flask for Gemini processing + Google Places validation
    let geminiResult = null;
    try {
      const geminiResponse = await axios.post(
        `${process.env.FLASK_BASE_URL}/suggestions/process`,
        {
          suggestion_text,
          disease    : diseaseText,
          campaign_id: campaign_id
        },
        {
          headers: { 'x-flask-secret': process.env.FLASK_INTERNAL_SECRET },
          timeout: 15000
        }
      );
      geminiResult = geminiResponse.data;
    } catch (err) {
      console.log('Gemini suggestion processing failed:', err.message);
    }

    // Only save if Google Places verified the hospital
    if (geminiResult?.google_places_verified) {
      await prisma.suggestion.create({
        data: {
          campaign_id           : parseInt(campaign_id),
          disease               : diseaseText,
          suggestion_text       : suggestion_text.trim(),
          hospital_name         : geminiResult.hospital_name || '',
          hospital_address      : geminiResult.hospital_address || '',
          google_places_verified: true
        }
      });

      // Notify patient in their native language
      if (campaign.patient?.email) {
        await notifyFlask('/notify/suggestion-received', {
          to_email      : campaign.patient.email,
          patient_name  : campaign.patient.name,
          campaign_title: campaign.title,
          disease       : diseaseText,
          suggestions   : [geminiResult],
          languages     : campaign.patient.native_languages || ['en']
        });
      }
    }

    res.json({
      success    : true,
      message    : 'Suggestion received and processed',
      verified   : geminiResult?.google_places_verified || false,
      hospital   : geminiResult?.google_places_verified
        ? { name: geminiResult.hospital_name, address: geminiResult.hospital_address }
        : null
    });

  } catch (error) {
    console.error('Suggestion error:', error);
    res.status(500).json({ success: false, error: 'Failed to process suggestion' });
  }
});

// ─────────────────────────────────────────
// POST /api/donations/webhook
// Razorpay webhook handler (server-side event)
// ─────────────────────────────────────────
router.post('/webhook', express.raw({ type: 'application/json' }), async (req, res) => {
  try {
    const webhookSecret = process.env.RAZORPAY_WEBHOOK_SECRET;
    const signature     = req.headers['x-razorpay-signature'];

    if (webhookSecret && signature) {
      const expectedSig = crypto
        .createHmac('sha256', webhookSecret)
        .update(req.body)
        .digest('hex');

      if (expectedSig !== signature) {
        return res.status(400).json({ success: false, error: 'Invalid webhook signature' });
      }
    }

    const event = JSON.parse(req.body.toString());
    console.log('Razorpay webhook event:', event.event);

    // Handle payment failed
    if (event.event === 'payment.failed') {
      const orderId = event.payload.payment?.entity?.order_id;
      if (orderId) {
        await prisma.donation.updateMany({
          where: { order_id: orderId, status: 'PENDING' },
          data : { status: 'FAILED' }
        }).catch(() => {});
      }
    }

    res.json({ success: true });
  } catch (error) {
    console.error('Webhook error:', error);
    res.status(500).json({ success: false });
  }
});

module.exports = router;