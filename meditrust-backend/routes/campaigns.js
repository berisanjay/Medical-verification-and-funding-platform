const express = require('express');
const router = express.Router();
const prisma = require('../utils/prisma');
const { verifyToken } = require('../middleware/auth');
const { createOTP, verifyOTP } = require('../utils/otp');
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');
const QRCode = require('qrcode');

// ─────────────────────────────────────────
// HELPER — Call HMS
// ─────────────────────────────────────────
const callHMS = async (method, path, data = null) => {
  const url = `${process.env.HMS_BASE_URL}${path}`;
  const config = { method, url };
  if (data) config.data = data;
  const response = await axios(config);
  return response.data;
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
// STEP 1 — Request OTP before campaign creation
// ─────────────────────────────────────────
router.post('/request-otp', verifyToken, async (req, res) => {
  try {
    const user = await prisma.user.findUnique({
      where: { id: req.user.id }
    });

    if (user.is_blacklisted) {
      return res.status(403).json({
        success: false,
        error: 'Your account is suspended'
      });
    }

    await createOTP(req.user.id, user.email, 'CAMPAIGN_CREATION');

    res.json({
      success: true,
      message: 'OTP sent to your email. Enter OTP to proceed with campaign creation.'
    });

  } catch (error) {
    console.error('Campaign OTP error:', error);
    res.status(500).json({ success: false, error: 'Failed to send OTP' });
  }
});

// ─────────────────────────────────────────
// STEP 2 — Create Campaign (after OTP verified)
// ─────────────────────────────────────────
router.post('/', verifyToken, async (req, res) => {
  try {
    const {
      otp_code,
      patient_full_name,
      patient_age,
      patient_gender,
      patient_aadhaar,
      patient_city,
      patient_state,
      patient_languages,
      relationship_to_fundraiser,
      title
    } = req.body;

    // OTP DISABLED FOR DEVELOPMENT — re-enable before production
    // const otpResult = await verifyOTP(req.user.id, otp_code, 'CAMPAIGN_CREATION');
    // if (!otpResult.valid) {
    //   return res.status(400).json({ success: false, error: otpResult.error });
    // }

    // Check fundraiser blacklist
    const fundraiser = await prisma.user.findUnique({
      where: { id: req.user.id }
    });
    if (fundraiser.is_blacklisted) {
      return res.status(403).json({
        success: false,
        error: 'Your account is suspended'
      });
    }

    // Check patient aadhaar blacklist
    const blacklisted = await prisma.blacklist.findUnique({
      where: { aadhaar_number: patient_aadhaar }
    });
    if (blacklisted) {
      return res.status(403).json({
        success: false,
        error: 'This patient Aadhaar is blacklisted'
      });
    }

    // Create campaign in DRAFT status
    const campaign = await prisma.campaign.create({
      data: {
        patient_id                 : req.user.id,
        patient_full_name,
        patient_age                : parseInt(patient_age),
        patient_gender,
        patient_aadhaar,
        patient_city,
        patient_state,
        patient_languages          : patient_languages || ['en'],
        relationship_to_fundraiser : relationship_to_fundraiser || 'SELF',
        title,
        status                     : 'DRAFT'
      }
    });

    res.status(201).json({
      success    : true,
      message    : 'Campaign created. Please upload documents for verification.',
      campaign_id: campaign.id
    });

  } catch (error) {
    console.error('Create campaign error:', error);
    res.status(500).json({ success: false, error: 'Failed to create campaign' });
  }
});

// ─────────────────────────────────────────
// PREVIEW VERIFY — Extract entities WITHOUT creating a campaign
// Called from Step 4 of create-campaign.html
// No campaign_id needed — just calls Flask /verify and returns extracted_data
// ─────────────────────────────────────────
router.post('/preview-verify', verifyToken, async (req, res) => {
  try {
    const { documents, patient_name } = req.body;

    if (!documents || documents.length === 0) {
      return res.status(400).json({ success: false, error: 'Documents required' });
    }

    console.log('\n🔍 === PREVIEW VERIFY (no campaign) ===');
    console.log('📄 Documents:', documents.length);
    console.log('👤 Patient:', patient_name);

    // Map documents for Flask
    const flaskDocs = documents.map(doc => ({
      document_type: doc.document_type,
      file_name    : doc.file_name,
      file_content : doc.file_url.includes('base64,')
        ? doc.file_url.split('base64,')[1]
        : doc.file_url,
      mime_type    : doc.file_url.includes('data:')
        ? doc.file_url.split(';')[0].replace('data:', '')
        : 'application/pdf'
    }));

    // Call Flask /verify
    const verificationResponse = await axios.post(
      `${process.env.FLASK_BASE_URL}/verify`,
      { patient_name: patient_name || 'Patient', documents: flaskDocs },
      {
        headers: {
          'x-flask-secret': process.env.FLASK_INTERNAL_SECRET,
          'Content-Type'  : 'application/json'
        },
        timeout         : 120000,
        maxBodyLength   : Infinity,
        maxContentLength: Infinity
      }
    ).catch(err => {
      console.error('❌ Flask preview-verify failed:', err.message);
      // Return error — do NOT fake a PENDING result
      return { data: { success: false, error: 'Flask AI service is not responding: ' + err.message } };
    });

    const verResult = verificationResponse.data;

    // If Flask failed — return error, don't fake a result
    if (!verResult.final_status && verResult.error) {
      return res.status(503).json({
        success: false,
        error  : 'AI service unavailable: ' + verResult.error,
        hint   : 'Make sure Flask is running on port 5000 (python app.py)'
      });
    }

    console.log('✅ Preview result:', verResult.final_status, '| Risk:', verResult.risk_score);
    console.log('📋 Extracted:', JSON.stringify(verResult.extracted_data, null, 2));

    res.json({
      success              : true,
      status               : verResult.final_status,
      risk_score           : verResult.risk_score || 0,
      extracted_data       : verResult.extracted_data || {},
      cross_document_issues: verResult.cross_document_issues || [],
      has_tampering        : verResult.has_tampering || false,
      has_expired_docs     : verResult.has_expired_docs || false,
      document_results     : verResult.document_results || []
    });

  } catch (error) {
    console.error('Preview verify error:', error);
    res.status(500).json({ success: false, error: 'Preview verification failed: ' + error.message });
  }
});

// ─────────────────────────────────────────
// STEP 3 — Submit Documents for Verification
// ─────────────────────────────────────────
router.post('/:id/verify-documents', verifyToken, async (req, res) => {
  try {
    console.log('=== VERIFY DOCUMENTS CALLED ===');
    console.log('Campaign ID:', req.params.id);
    console.log('Docs count:', req.body.documents?.length);
    const campaignId = parseInt(req.params.id);
    const { documents } = req.body;

    // documents = array of { document_type, file_url, file_name }
    if (!documents || documents.length === 0) {
      return res.status(400).json({
        success: false,
        error: 'Documents required'
      });
    }

    const campaign = await prisma.campaign.findUnique({
      where: { id: campaignId }
    });

    if (!campaign || campaign.patient_id !== req.user.id) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    // Save documents to DB
    await prisma.campaignDocument.createMany({
      data: documents.map(doc => ({
        campaign_id  : campaignId,
        document_type: doc.document_type,
        file_url     : doc.file_url,
        file_name    : doc.file_name
      }))
    });

    // Update campaign status
    await prisma.campaign.update({
      where: { id: campaignId },
      data : { status: 'PENDING_VERIFICATION' }
    });

    // Call Flask AI verification — send actual documents
    const flaskDocs = documents.map(doc => ({
      document_type: doc.document_type,
      file_name    : doc.file_name,
      file_content : doc.file_url.includes('base64,')
        ? doc.file_url.split('base64,')[1]
        : doc.file_url,
      mime_type    : doc.file_url.includes('data:')
        ? doc.file_url.split(';')[0].replace('data:', '')
        : 'application/pdf'
    }));

    console.log('\n🔍 === DOCUMENT VERIFICATION STARTED ===');
    console.log('📋 Campaign ID:', campaignId);
    console.log('👤 Patient Name:', campaign.patient_full_name);
    console.log('📄 Documents to verify:', documents.length);
    console.log('📦 Doc types:', flaskDocs.map(d => d.document_type).join(', '));
    console.log('📏 Approx payload size:', Math.round(JSON.stringify(flaskDocs).length / 1024), 'KB');
    console.log('🌐 Flask URL:', process.env.FLASK_BASE_URL);
    console.log('🔑 Flask secret set:', !!process.env.FLASK_INTERNAL_SECRET);
    console.log('📤 Sending to Flask AI Service...');

    const verificationResponse = await axios.post(
      `${process.env.FLASK_BASE_URL}/verify`,
      {
        patient_name: campaign.patient_full_name,
        documents   : flaskDocs
      },
      {
        headers: {
          'x-flask-secret': process.env.FLASK_INTERNAL_SECRET,
          'Content-Type'  : 'application/json'
        },
        timeout         : 120000,
        maxBodyLength   : Infinity,
        maxContentLength: Infinity
      }
    ).catch(err => {
      console.error('❌ Flask verification failed:', err.message);
      return { data: { success: false, error: 'Flask AI service is not responding: ' + err.message } };
    });

    const verResult = verificationResponse.data;

    // If Flask failed — return error to frontend, don't fake a result
    if (!verResult.final_status && verResult.error) {
      return res.status(503).json({
        success: false,
        error  : 'AI verification service unavailable: ' + verResult.error,
        hint   : 'Make sure Flask is running on port 5000 (python app.py)'
      });
    }
    console.log('\n📥 === FLASK AI VERIFICATION RESULTS ===');
    console.log('🎯 Final Status:', verResult.final_status);
    console.log('⚠️  Risk Score:', verResult.risk_score);
    console.log('🔒 Has Tampering:', verResult.has_tampering);
    console.log('⏰ Has Expired Docs:', verResult.has_expired_docs);
    console.log('📊 Cross-Document Issues:', verResult.cross_document_issues || []);
    console.log('📋 Extracted Data:', JSON.stringify(verResult.extracted_data, null, 2));

    // Log individual document results
    if (verResult.document_results && verResult.document_results.length > 0) {
      console.log('\n📄 === INDIVIDUAL DOCUMENT RESULTS ===');
      verResult.document_results.forEach((doc, index) => {
        console.log(`\n📋 Document ${index + 1}: ${doc.file_name}`);
        console.log(`   Type: ${doc.document_type}`);
        console.log(`   Status: ${doc.status}`);
        if (doc.error) {
          console.log(`   ❌ Error: ${doc.error}`);
        }
        if (doc.entities) {
          console.log(`   🏥 Hospital: ${doc.entities.hospital_name || 'Not found'}`);
          console.log(`   👤 Patient: ${doc.entities.patient_name || 'Not found'}`);
          console.log(`   🩺 Disease: ${doc.entities.disease || 'Not found'}`);
          console.log(`   💰 Amount: ${doc.entities.amount || 'Not found'}`);
          console.log(`   📅 Date: ${doc.entities.date || 'Not found'}`);
        }
      });
    }

    // Map Flask status to our status
    const statusMap = {
      'VERIFIED'            : 'VERIFIED',
      'PENDING'             : 'PENDING',
      'VERIFICATION_NEEDED' : 'VERIFICATION_NEEDED',
      'UPDATE_NEEDED'       : 'UPDATE_NEEDED'
    };
    const newStatus = statusMap[verResult.final_status] || 'PENDING';

    console.log('\n🔄 === STATUS MAPPING ===');
    console.log('📋 Flask Status:', verResult.final_status);
    console.log('🎯 Our Status:', newStatus);

    // Determine what action is needed
    let actionRequired = 'NONE';
    let statusMessage = '';

    switch (newStatus) {
      case 'VERIFIED':
        statusMessage = '✅ All documents verified successfully! Campaign approved.';
        break;
      case 'PENDING':
        actionRequired = 'ADMIN_REVIEW';
        statusMessage = '⏳ Documents submitted. Minor issues detected - pending admin review.';
        break;
      case 'VERIFICATION_NEEDED':
        actionRequired = 'ADMIN_REVIEW_URGENT';
        statusMessage = '🚨 Serious issues detected! Urgent admin review required.';
        break;
      case 'UPDATE_NEEDED':
        actionRequired = 'PATIENT_UPDATE';
        statusMessage = '📝 Some documents expired. Please upload updated documents.';
        break;
      default:
        statusMessage = '❓ Unknown status. Please contact support.';
    }

    console.log('⚡ Action Required:', actionRequired);
    console.log('💬 Status Message:', statusMessage);

    // Save verification record
    const verificationRecord = await prisma.verificationRecord.create({
      data: {
        campaign_id   : campaignId,
        status        : newStatus,
        extracted_data: verResult.extracted_data || {},
        issues        : verResult.cross_document_issues || [],
        risk_score    : verResult.risk_score || 0,
        has_expired   : verResult.has_expired_docs || false,
        has_tampering : verResult.has_tampering || false
      }
    });

    console.log('\n💾 === DATABASE SAVED ===');
    console.log('📋 Verification Record ID:', verificationRecord.id);
    console.log('🎯 Campaign Status Updated:', newStatus);

    // Update campaign with extracted data from documents
    const extracted = verResult.extracted_data || {};
    const updatedCampaign = await prisma.campaign.update({
      where: { id: campaignId },
      data : {
        status          : newStatus,
        verified_amount : extracted.amount
          ? parseFloat(extracted.amount.toString().replace(/[^0-9.]/g, ''))
          : null
      }
    });

    console.log('\n💰 === EXTRACTED FINANCIAL DATA ===');
    console.log('💵 Verified Amount:', extracted.amount || 'Not found');
    console.log('🏥 Hospital:', extracted.hospital_name || 'Not found');
    console.log('👤 Patient Name Match:', extracted.patient_name === campaign.patient_full_name ? '✅ MATCH' : '❌ MISMATCH');

    console.log('\n🎉 === VERIFICATION COMPLETE ===');
    console.log('📊 Final Summary:');
    console.log(`   - Status: ${newStatus}`);
    console.log(`   - Risk Score: ${verResult.risk_score}`);
    console.log(`   - Documents Processed: ${verResult.document_results?.length || 0}`);
    console.log(`   - Issues Found: ${verResult.cross_document_issues?.length || 0}`);
    console.log(`   - Action Required: ${actionRequired}`);
    console.log('=====================================\n');

    res.json({
      success   : true,
      status    : newStatus,
      risk_score: verResult.risk_score,
      action_required: actionRequired,
      message   : statusMessage,
      verification_details: {
        final_status          : verResult.final_status,
        has_tampering         : verResult.has_tampering,
        has_expired_docs      : verResult.has_expired_docs,
        cross_document_issues : verResult.cross_document_issues || [],
        document_results      : verResult.document_results || [],
        extracted_data        : verResult.extracted_data || {}
      },
      extracted_data: extracted
    });

  } catch (error) {
    console.error('Verify documents error:', error);
    res.status(500).json({ success: false, error: 'Document verification failed' });
  }
});
 // Notification disabled temporarily
// await notifyFlask('/notify/verification-status', {...});
// ─────────────────────────────────────────
// STEP 4 — Go LIVE (after story approved)
// ─────────────────────────────────────────
router.post('/:id/go-live', verifyToken, async (req, res) => {
  try {
    const campaignId = parseInt(req.params.id);

    const campaign = await prisma.campaign.findUnique({
      where  : { id: campaignId },
      include: { patient: true }
    });

    if (!campaign || campaign.patient_id !== req.user.id) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    if (campaign.status !== 'VERIFIED' || !campaign.story_approved) {
      return res.status(400).json({
        success: false,
        error: 'Campaign must be verified and story approved before going live'
      });
    }

    // Generate unique public URL
    const publicUrl = `meditrust.in/campaign/${uuidv4().split('-')[0]}`;

    // Generate UPI ID
    const upiId = `meditrust.${campaignId}@ybl`;

    // Generate QR code
    const qrCodeUrl = await QRCode.toDataURL(
      `upi://pay?pa=${upiId}&pn=MediTrust&tn=Campaign-${campaignId}`
    );

    // Set expiry — 90 days from now
    const expiresAt = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000);

    // Update campaign to LIVE
    await prisma.campaign.update({
      where: { id: campaignId },
      data : {
        status    : 'LIVE_CAMPAIGN',
        public_url: publicUrl,
        upi_id    : upiId,
        qr_code_url: qrCodeUrl,
        expires_at: expiresAt
      }
    });

    // Notify patient
    await notifyFlask('/notify/campaign-live', {
      to_email       : campaign.patient.email,
      patient_name   : campaign.patient_full_name,
      campaign_title : campaign.title,
      public_url     : publicUrl,
      upi_id         : upiId
    });

    res.json({
      success   : true,
      message   : 'Campaign is now LIVE!',
      public_url: publicUrl,
      upi_id    : upiId,
      expires_at: expiresAt
    });

  } catch (error) {
    console.error('Go live error:', error);
    res.status(500).json({ success: false, error: 'Failed to go live' });
  }
});

// ─────────────────────────────────────────
// GET ALL LIVE CAMPAIGNS (Public)
// ─────────────────────────────────────────
router.get('/', async (req, res) => {
  try {
    const page   = parseInt(req.query.page  || '1');
    const limit  = parseInt(req.query.limit || '10');
    const skip   = (page - 1) * limit;
    const search = req.query.search || '';

    const where = {
      status: 'LIVE_CAMPAIGN',
      ...(search && {
        OR: [
          { title             : { contains: search } },
          { patient_full_name : { contains: search } }
        ]
      })
    };

    const [campaigns, total] = await Promise.all([
      prisma.campaign.findMany({
        where,
        skip,
        take   : limit,
        select : {
          id               : true,
          title            : true,
          patient_full_name: true,
          verified_amount  : true,
          collected_amount : true,
          released_amount  : true,
          public_url       : true,
          upi_id           : true,
          qr_code_url      : true,
          story_gemini     : true,
          status           : true,
          created_at       : true,
          hospital         : true
        },
        orderBy: { created_at: 'desc' }
      }),
      prisma.campaign.count({ where })
    ]);

    res.json({ success: true, campaigns, total, page, limit });

  } catch (error) {
    console.error('Get campaigns error:', error);
    res.status(500).json({ success: false, error: 'Failed to get campaigns' });
  }
});

// ─────────────────────────────────────────
// GET SINGLE CAMPAIGN (Public)
// ─────────────────────────────────────────
router.get('/:id', async (req, res) => {
  try {
    const campaign = await prisma.campaign.findUnique({
      where  : { id: parseInt(req.params.id) },
      include: {
        hospital : true,
        donations: {
          where  : { status: 'SUCCESS' },
          select : {
            donor_name  : true,
            is_anonymous: true,
            amount      : true,
            donated_at  : true
          },
          orderBy: { donated_at: 'desc' },
          take   : 20
        },
        updates  : {
          orderBy: { created_at: 'desc' }
        },
        fund_releases: {
          where  : { status: 'COMPLETED' },
          orderBy: { released_at: 'desc' }
        }
      }
    });

    if (!campaign) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    // Hide anonymous donor names
    campaign.donations = campaign.donations.map(d => ({
      ...d,
      donor_name: d.is_anonymous ? 'Anonymous Donor' : d.donor_name
    }));

    res.json({ success: true, campaign });

  } catch (error) {
    console.error('Get campaign error:', error);
    res.status(500).json({ success: false, error: 'Failed to get campaign' });
  }
});

// ─────────────────────────────────────────
// GET PATIENT'S OWN CAMPAIGNS
// ─────────────────────────────────────────
router.get('/my/campaigns', verifyToken, async (req, res) => {
  try {
    const campaigns = await prisma.campaign.findMany({
      where  : { patient_id: req.user.id },
      include: {
        verification_records: { orderBy: { verified_at: 'desc' }, take: 1 },
        fund_releases       : { orderBy: { released_at: 'desc' } },
        donations           : { where: { status: 'SUCCESS' } }
      },
      orderBy: { created_at: 'desc' }
    });

    res.json({ success: true, campaigns });

  } catch (error) {
    console.error('Get my campaigns error:', error);
    res.status(500).json({ success: false, error: 'Failed to get campaigns' });
  }
});

// ─────────────────────────────────────────
// PATIENT ANALYTICS
// ─────────────────────────────────────────
router.get('/:id/analytics', verifyToken, async (req, res) => {
  try {
    const campaignId = parseInt(req.params.id);

    const campaign = await prisma.campaign.findUnique({
      where: { id: campaignId }
    });

    if (!campaign || campaign.patient_id !== req.user.id) {
      return res.status(403).json({ success: false, error: 'Unauthorized' });
    }

    const [
      totalDonations,
      donorCount,
      fundReleases,
      ngoMatches,
      updates
    ] = await Promise.all([
      prisma.donation.aggregate({
        where: { campaign_id: campaignId, status: 'SUCCESS' },
        _sum : { amount: true },
        _count: true
      }),
      prisma.donation.count({
        where: { campaign_id: campaignId, status: 'SUCCESS' }
      }),
      prisma.fundRelease.findMany({
        where  : { campaign_id: campaignId },
        orderBy: { released_at: 'desc' }
      }),
      prisma.nGOMatch.findMany({
        where  : { campaign_id: campaignId },
        include: { ngo: { select: { name: true, email: true } } }
      }),
      prisma.campaignUpdate.count({
        where: { campaign_id: campaignId }
      })
    ]);

    res.json({
      success  : true,
      analytics: {
        total_raised    : totalDonations._sum.amount || 0,
        donor_count     : donorCount,
        fund_releases   : fundReleases,
        ngo_matches     : ngoMatches,
        updates_posted  : updates,
        collected_amount: campaign.collected_amount,
        released_amount : campaign.released_amount,
        verified_amount : campaign.verified_amount
      }
    });

  } catch (error) {
    console.error('Analytics error:', error);
    res.status(500).json({ success: false, error: 'Failed to get analytics' });
  }
});

// ─────────────────────────────────────────
// POST CAMPAIGN UPDATE
// ─────────────────────────────────────────
router.post('/:id/updates', verifyToken, async (req, res) => {
  try {
    const campaignId               = parseInt(req.params.id);
    const { update_text, is_milestone } = req.body;

    const campaign = await prisma.campaign.findUnique({
      where  : { id: campaignId },
      include: { patient: true }
    });

    if (!campaign || campaign.patient_id !== req.user.id) {
      return res.status(403).json({ success: false, error: 'Unauthorized' });
    }

    const update = await prisma.campaignUpdate.create({
      data: {
        campaign_id : campaignId,
        update_text,
        is_milestone: is_milestone || false,
        notify_donors: is_milestone || false
      }
    });

    // Only notify donors on milestone updates
    if (is_milestone) {
      const donors = await prisma.donation.findMany({
        where: { campaign_id: campaignId, status: 'SUCCESS', is_anonymous: false }
      });

      for (const donor of donors) {
        await notifyFlask('/notify/campaign-update', {
          to_email       : donor.donor_email,
          donor_name     : donor.donor_name,
          campaign_title : campaign.title,
          update_text
        });
      }
    }

    res.status(201).json({ success: true, update });

  } catch (error) {
    console.error('Post update error:', error);
    res.status(500).json({ success: false, error: 'Failed to post update' });
  }
});

module.exports = router;
// ─────────────────────────────────────────
// HOSPITAL CHANGE FLOW
// OTP required → suspend payouts → re-verify
// ─────────────────────────────────────────
router.put('/:id/hospital-change', verifyToken, async (req, res) => {
  try {
    const campaignId = parseInt(req.params.id);
    const { otp_code, new_hospital_name, new_hospital_id, documents } = req.body;

    // Verify OTP
    // OTP DISABLED FOR DEVELOPMENT — re-enable before production
    // const otpResult = await verifyOTP(req.user.id, otp_code, 'HOSPITAL_CHANGE');
    // if (!otpResult.valid) {
    //   return res.status(400).json({ success: false, error: otpResult.error });
    // }

    const campaign = await prisma.campaign.findUnique({
      where  : { id: campaignId },
      include: { patient: true }
    });

    if (!campaign || campaign.patient_id !== req.user.id) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    if (!['LIVE_CAMPAIGN', 'LIVE_UPDATED'].includes(campaign.status)) {
      return res.status(400).json({
        success: false,
        error  : 'Hospital change only allowed on live campaigns'
      });
    }

    if (!documents || documents.length === 0) {
      return res.status(400).json({
        success: false,
        error  : 'New hospital documents required for hospital change'
      });
    }

    // Save new documents
    await prisma.campaignDocument.createMany({
      data: documents.map(doc => ({
        campaign_id  : campaignId,
        document_type: doc.document_type,
        file_url     : doc.file_url,
        file_name    : doc.file_name
      }))
    });

    // Suspend payouts — status → HOSPITAL_CHANGE_REQUESTED
    await prisma.campaign.update({
      where: { id: campaignId },
      data : {
        status     : 'HOSPITAL_CHANGE_REQUESTED',
        hospital_id: new_hospital_id ? parseInt(new_hospital_id) : campaign.hospital_id
      }
    });

    // Run AI re-verification on new documents
    const flaskDocs = documents.map(doc => ({
      document_type: doc.document_type,
      file_name    : doc.file_name,
      file_content : doc.file_url.includes('base64,')
        ? doc.file_url.split('base64,')[1]
        : doc.file_url,
      mime_type    : doc.file_url.includes('data:')
        ? doc.file_url.split(';')[0].replace('data:', '')
        : 'application/pdf'
    }));

    // Update status to REVERIFYING
    await prisma.campaign.update({
      where: { id: campaignId },
      data : { status: 'REVERIFYING' }
    });

    // Call Flask AI for re-verification
    const verificationResponse = await axios.post(
      `${process.env.FLASK_BASE_URL}/verify`,
      { patient_name: campaign.patient_full_name, documents: flaskDocs },
      {
        headers : { 'x-flask-secret': process.env.FLASK_INTERNAL_SECRET },
        timeout : 120000,
        maxBodyLength   : Infinity,
        maxContentLength: Infinity
      }
    ).catch(err => {
      console.error('Flask re-verification failed:', err.message);
      return { data: { final_status: 'PENDING', risk_score: 50, extracted_data: {}, document_results: [] } };
    });

    const verResult = verificationResponse.data;

    // Save new verification record
    await prisma.verificationRecord.create({
      data: {
        campaign_id   : campaignId,
        status        : verResult.final_status || 'PENDING',
        extracted_data: verResult.extracted_data || {},
        issues        : verResult.cross_document_issues || [],
        risk_score    : verResult.risk_score || 0,
        has_expired   : verResult.has_expired_docs || false,
        has_tampering : verResult.has_tampering || false
      }
    });

    // If VERIFIED — resume campaign as LIVE_UPDATED
    if (verResult.final_status === 'VERIFIED') {
      await prisma.campaign.update({
        where: { id: campaignId },
        data : { status: 'LIVE_UPDATED' }
      });

      // Notify patient — hospital change approved
      await notifyFlask('/notify/verification-status', {
        to_email      : campaign.patient.email,
        patient_name  : campaign.patient_full_name,
        status        : 'HOSPITAL_CHANGE_APPROVED',
        campaign_title: campaign.title
      });

      return res.json({
        success: true,
        message: 'Hospital change verified. Campaign is now LIVE with new hospital.',
        status : 'LIVE_UPDATED'
      });
    }

    // If PENDING or VERIFICATION_NEEDED — admin must review
    res.json({
      success: true,
      message: `Hospital change submitted. Status: ${verResult.final_status}. Admin will review.`,
      status : verResult.final_status
    });

  } catch (error) {
    console.error('Hospital change error:', error);
    res.status(500).json({ success: false, error: 'Hospital change failed' });
  }
});

// ─────────────────────────────────────────
// REQUEST OTP FOR HOSPITAL CHANGE
// ─────────────────────────────────────────
router.post('/:id/hospital-change-otp', verifyToken, async (req, res) => {
  try {
    const user = await prisma.user.findUnique({ where: { id: req.user.id } });

    await createOTP(req.user.id, user.email, 'HOSPITAL_CHANGE');

    res.json({
      success: true,
      message: 'OTP sent to your email. Enter OTP to confirm hospital change.'
    });
  } catch (error) {
    console.error('Hospital change OTP error:', error);
    res.status(500).json({ success: false, error: 'Failed to send OTP' });
  }
});