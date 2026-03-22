const express = require('express');
const router = express.Router();
const prisma = require('../utils/prisma');
const { verifyAdmin } = require('../middleware/auth');
const axios = require('axios');

// ─────────────────────────────────────────
// HELPER — Call HMS
// ─────────────────────────────────────────
const callHMS = async (method, path, data = null) => {
  try {
    const url      = `${process.env.HMS_BASE_URL}${path}`;
    const config   = { method, url };
    if (data) config.data = data;
    const response = await axios(config);
    return response.data;
  } catch (err) {
    console.log(`HMS call failed ${path}:`, err.message);
    return null;
  }
};

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
// TRIGGER FUND RELEASE — Admin only
// 3 pre-release checks before every payout
// ─────────────────────────────────────────
router.post('/trigger', verifyAdmin, async (req, res) => {
  try {
    const { campaign_id, amount } = req.body;

    if (!campaign_id || !amount) {
      return res.status(400).json({
        success: false,
        error: 'campaign_id and amount required'
      });
    }

    const campaign = await prisma.campaign.findUnique({
      where  : { id: parseInt(campaign_id) },
      include: { patient: true, hospital: true }
    });

    if (!campaign) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    if (campaign.status !== 'LIVE_CAMPAIGN') {
      return res.status(400).json({
        success: false,
        error  : `Cannot release funds — campaign status is ${campaign.status}`
      });
    }

    // ── Get FundNeeder billing data (fallback if no HMS ID) ──
    let fundNeeder = null;
    try {
      fundNeeder = await prisma.fundNeeder.findUnique({
        where: { campaign_id: parseInt(campaign_id) }
      });
    } catch(e) {
      console.log('FundNeeder lookup failed:', e.message);
    }

    // If no HMS ID and no FundNeeder — still allow release with admin override
    if (!campaign.patient_hms_id && !fundNeeder) {
      console.log('⚠️ No HMS ID or FundNeeder — admin proceeding with manual release');
    }

    // ── PRE-RELEASE CHECK 1: Hospital still verified? ──
    const verificationRecord = await prisma.verificationRecord.findFirst({
      where  : { campaign_id: parseInt(campaign_id) },
      orderBy: { verified_at: 'desc' }
    });

    if (!verificationRecord || verificationRecord.status !== 'VERIFIED') {
      await prisma.fundRelease.create({
        data: {
          campaign_id  : parseInt(campaign_id),
          amount       : parseFloat(amount),
          triggered_by : 'ADMIN',
          status       : 'BLOCKED',
          block_reason : 'Hospital not verified'
        }
      });
      return res.status(400).json({
        success: false,
        error  : 'BLOCKED — Hospital not verified'
      });
    }

    // ── PRE-RELEASE CHECK 2: Patient still active in HMS? ──
    let hmsStatus = null;
    if (campaign.patient_hms_id) {
      hmsStatus = await callHMS('GET', `/hms/patients/${campaign.patient_hms_id}/status`);
      if (hmsStatus && hmsStatus.status === 'DISCHARGED') {
        await prisma.fundRelease.create({
          data: {
            campaign_id  : parseInt(campaign_id),
            amount       : parseFloat(amount),
            triggered_by : 'ADMIN',
            status       : 'BLOCKED',
            block_reason : 'Patient already discharged'
          }
        });
        return res.status(400).json({
          success: false,
          error  : 'BLOCKED — Patient already discharged'
        });
      }
    } else {
      console.log('⚠️ No HMS ID — skipping HMS status check');
    }

    // ── PRE-RELEASE CHECK 3: Outstanding amount > 0? ──
    let outstanding = null;
    if (campaign.patient_hms_id) {
      outstanding = await callHMS(
        'GET',
        `/hms/patients/${campaign.patient_hms_id}/outstanding`
      );
    }

    // If no HMS — use FundNeeder outstanding or campaign verified_amount
    if (!outstanding) {
      const outstandingAmount = fundNeeder
        ? parseFloat(fundNeeder.outstanding)
        : parseFloat(campaign.verified_amount || amount);
      outstanding = { outstanding: outstandingAmount };
      console.log('⚠️ Using FundNeeder/verified_amount for outstanding:', outstandingAmount);
    }

    if (!outstanding || parseFloat(outstanding.outstanding) <= 0) {
      await prisma.campaign.update({
        where: { id: parseInt(campaign_id) },
        data : { status: 'COMPLETED' }
      });
      return res.status(400).json({
        success: false,
        error  : 'Outstanding amount is zero — campaign marked COMPLETED'
      });
    }

    // ── All 3 checks passed — Release funds ──
    const releaseAmount = Math.min(
      parseFloat(amount),
      parseFloat(outstanding.outstanding)
    );

    // Create release record
    const release = await prisma.fundRelease.create({
      data: {
        campaign_id  : parseInt(campaign_id),
        amount       : releaseAmount,
        triggered_by : 'ADMIN',
        status       : 'APPROVED'
      }
    });

    // Update HMS ledger — only if HMS ID exists
    let hmsPayment = null;
    if (campaign.patient_hms_id) {
      hmsPayment = await callHMS('POST', '/hms/payments', {
        patient_hms_id: campaign.patient_hms_id,
        amount        : releaseAmount,
        source        : 'MediTrust Crowdfunding',
        notes         : `Campaign ${campaign_id} — Release ${release.id}`
      });
    }

    // Update release status
    await prisma.fundRelease.update({
      where: { id: release.id },
      data : {
        hms_payment_id: hmsPayment?.payment?.id?.toString() || null,
        status        : 'COMPLETED'
      }
    });

    // Update campaign released amount
    await prisma.campaign.update({
      where: { id: parseInt(campaign_id) },
      data : {
        released_amount: { increment: releaseAmount }
      }
    });

    // Log admin action
    await prisma.adminAuditLog.create({
      data: {
        admin_id    : req.admin.id,
        action      : 'FUND_RELEASED',
        target_type : 'campaign',
        target_id   : parseInt(campaign_id),
        notes       : `Released Rs. ${releaseAmount} to hospital`
      }
    });

    // Notify patient
    await notifyFlask('/notify/fund-release', {
      to_email            : campaign.patient.email,
      patient_name        : campaign.patient_full_name,
      campaign_title      : campaign.title,
      amount_released     : releaseAmount,
      outstanding_remaining: parseFloat(outstanding.outstanding) - releaseAmount
    });

    // Check if fully funded after this release
    const updatedCampaign = await prisma.campaign.findUnique({
      where: { id: parseInt(campaign_id) }
    });

    if (
      updatedCampaign.verified_amount &&
      parseFloat(updatedCampaign.released_amount) >=
      parseFloat(updatedCampaign.verified_amount)
    ) {
      await prisma.campaign.update({
        where: { id: parseInt(campaign_id) },
        data : { status: 'COMPLETED' }
      });
    }

    res.json({
      success          : true,
      message          : `Rs. ${releaseAmount} released to hospital successfully`,
      release_id       : release.id,
      amount_released  : releaseAmount,
      outstanding_before: outstanding.outstanding,
      outstanding_after : parseFloat(outstanding.outstanding) - releaseAmount
    });

  } catch (error) {
    console.error('Fund release error:', error);
    res.status(500).json({ success: false, error: 'Fund release failed' });
  }
});

// ─────────────────────────────────────────
// GET RELEASES FOR A CAMPAIGN
// ─────────────────────────────────────────
router.get('/campaign/:campaign_id', async (req, res) => {
  try {
    const releases = await prisma.fundRelease.findMany({
      where  : { campaign_id: parseInt(req.params.campaign_id) },
      orderBy: { released_at: 'desc' }
    });

    res.json({ success: true, releases });

  } catch (error) {
    console.error('Get releases error:', error);
    res.status(500).json({ success: false, error: 'Failed to get releases' });
  }
});

// ─────────────────────────────────────────
// GET ALL PENDING RELEASES — Admin
// ─────────────────────────────────────────
router.get('/pending', verifyAdmin, async (req, res) => {
  try {
    const releases = await prisma.fundRelease.findMany({
      where  : { status: 'PENDING' },
      include: {
        campaign: {
          include: { patient: true, hospital: true }
        }
      },
      orderBy: { released_at: 'desc' }
    });

    res.json({ success: true, releases });

  } catch (error) {
    console.error('Get pending releases error:', error);
    res.status(500).json({ success: false, error: 'Failed to get pending releases' });
  }
});

module.exports = router;