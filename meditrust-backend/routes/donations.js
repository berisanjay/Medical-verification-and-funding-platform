const express = require('express');
const router = express.Router();
const prisma = require('../utils/prisma');
const axios = require('axios');
const Razorpay = require('razorpay');
const crypto = require('crypto');

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
      headers: { 'x-flask-secret': process.env.FLASK_INTERNAL_SECRET }
    });
  } catch (err) {
    console.log(`Notification failed ${path}:`, err.message);
  }
};

// ─────────────────────────────────────────
// INITIATE DONATION — Create Razorpay Order
// ─────────────────────────────────────────
router.post('/initiate', async (req, res) => {
  try {
    const { campaign_id, donor_name, donor_email, amount, is_anonymous } = req.body;

    if (!campaign_id || !donor_name || !donor_email || !amount) {
      return res.status(400).json({
        success: false,
        error: 'campaign_id, donor_name, donor_email and amount required'
      });
    }

    // Check campaign is live
    const campaign = await prisma.campaign.findUnique({
      where: { id: parseInt(campaign_id) }
    });

    if (!campaign || campaign.status !== 'LIVE_CAMPAIGN') {
      return res.status(400).json({
        success: false,
        error: 'Campaign is not active'
      });
    }

    // Create Razorpay order
    const order = await razorpay.orders.create({
      amount  : Math.round(parseFloat(amount) * 100), // paise
      currency: 'INR',
      notes   : {
        campaign_id: campaign_id.toString(),
        donor_email,
        donor_name
      }
    });

    // Create pending donation record
    const donation = await prisma.donation.create({
      data: {
        campaign_id : parseInt(campaign_id),
        donor_name,
        donor_email,
        is_anonymous: is_anonymous || false,
        amount      : parseFloat(amount),
        order_id    : order.id,
        status      : 'PENDING'
      }
    });

    res.json({
      success   : true,
      order_id  : order.id,
      amount    : order.amount,
      currency  : order.currency,
      donation_id: donation.id,
      key_id    : process.env.RAZORPAY_KEY_ID
    });

  } catch (error) {
    console.error('Initiate donation error:', error);
    res.status(500).json({ success: false, error: 'Failed to initiate donation' });
  }
});

// ─────────────────────────────────────────
// VERIFY DONATION — After Razorpay payment
// ─────────────────────────────────────────
router.post('/verify', async (req, res) => {
  try {
    const {
      donation_id,
      razorpay_order_id,
      razorpay_payment_id,
      razorpay_signature
    } = req.body;

    if (!razorpay_order_id || !razorpay_payment_id || !razorpay_signature) {
      return res.status(400).json({
        success: false,
        error: 'Payment details required'
      });
    }

    // Verify signature
    const body      = razorpay_order_id + '|' + razorpay_payment_id;
    const expected  = crypto
      .createHmac('sha256', process.env.RAZORPAY_KEY_SECRET)
      .update(body)
      .digest('hex');

    if (expected !== razorpay_signature) {
      return res.status(400).json({
        success: false,
        error: 'Payment verification failed — invalid signature'
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
      data : {
        collected_amount: {
          increment: donation.amount
        }
      }
    });

    // Get campaign details
    const campaign = await prisma.campaign.findUnique({
      where: { id: donation.campaign_id }
    });

    // Send receipt email via Flask
    if (!donation.is_anonymous) {
      await notifyFlask('/notify/donation-receipt', {
        to_email      : donation.donor_email,
        donor_name    : donation.donor_name,
        campaign_title: campaign.title,
        amount        : donation.amount,
        transaction_id: razorpay_payment_id,
        donated_at    : donation.donated_at
      });

      // Mark receipt as sent
      await prisma.donation.update({
        where: { id: donation.id },
        data : { receipt_sent: true }
      });
    }

    // Check if campaign is fully funded
    const updatedCampaign = await prisma.campaign.findUnique({
      where: { id: donation.campaign_id }
    });

    if (
      updatedCampaign.verified_amount &&
      updatedCampaign.collected_amount >= updatedCampaign.verified_amount
    ) {
      // Mark as completed
      await prisma.campaign.update({
        where: { id: donation.campaign_id },
        data : { status: 'COMPLETED' }
      });
    }

    res.json({
      success   : true,
      message   : 'Payment verified successfully',
      donation_id: donation.id,
      receipt_sent: !donation.is_anonymous
    });

  } catch (error) {
    console.error('Verify donation error:', error);
    res.status(500).json({ success: false, error: 'Payment verification failed' });
  }
});

// ─────────────────────────────────────────
// GET DONATIONS FOR A CAMPAIGN (Public)
// ─────────────────────────────────────────
router.get('/campaign/:campaign_id', async (req, res) => {
  try {
    const donations = await prisma.donation.findMany({
      where  : {
        campaign_id: parseInt(req.params.campaign_id),
        status     : 'SUCCESS'
      },
      select : {
        donor_name  : true,
        is_anonymous: true,
        amount      : true,
        donated_at  : true
      },
      orderBy: { donated_at: 'desc' }
    });

    // Hide anonymous donor names
    const cleaned = donations.map(d => ({
      ...d,
      donor_name: d.is_anonymous ? 'Anonymous Donor' : d.donor_name
    }));

    res.json({ success: true, donations: cleaned });

  } catch (error) {
    console.error('Get donations error:', error);
    res.status(500).json({ success: false, error: 'Failed to get donations' });
  }
});

// ─────────────────────────────────────────
// POST DONOR COMMENT / SUGGESTION
// ─────────────────────────────────────────
router.post('/suggest', async (req, res) => {
  try {
    const { campaign_id, suggestion_text } = req.body;

    if (!campaign_id || !suggestion_text) {
      return res.status(400).json({
        success: false,
        error: 'campaign_id and suggestion_text required'
      });
    }

    const campaign = await prisma.campaign.findUnique({
      where  : { id: parseInt(campaign_id) },
      include: { patient: true }
    });

    if (!campaign) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    // Send to Flask for Gemini processing + Google Places validation
    let geminiResult = null;
    try {
      const geminiResponse = await axios.post(
        `${process.env.FLASK_BASE_URL}/suggestions/process`,
        { suggestion_text, disease: campaign.patient_full_name },
        { headers: { 'x-flask-secret': process.env.FLASK_INTERNAL_SECRET } }
      );
      geminiResult = geminiResponse.data;
    } catch (err) {
      console.log('Gemini suggestion processing failed:', err.message);
    }

    // Only save if Google Places verified
    if (geminiResult && geminiResult.google_places_verified) {
      await prisma.suggestion.create({
        data: {
          campaign_id            : parseInt(campaign_id),
          disease                : campaign.patient_full_name,
          suggestion_text,
          hospital_name          : geminiResult.hospital_name,
          hospital_address       : geminiResult.hospital_address,
          google_places_verified : true
        }
      });

      // Notify patient
      await notifyFlask('/notify/suggestions', {
        to_email    : campaign.patient.email,
        patient_name: campaign.patient_full_name,
        disease     : campaign.patient_full_name,
        suggestions : [geminiResult]
      });
    }

    res.json({
      success : true,
      message : 'Suggestion received and processed',
      verified: geminiResult?.google_places_verified || false
    });

  } catch (error) {
    console.error('Suggestion error:', error);
    res.status(500).json({ success: false, error: 'Failed to process suggestion' });
  }
});

module.exports = router;