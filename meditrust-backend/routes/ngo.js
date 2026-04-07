/**
 * MediTrust - NGO Matching System
 * Phase 11
 *
 * Flow:
 *   1. Campaign goes LIVE
 *   2. POST /api/ngo/match/:campaign_id  -> find best NGOs from ngo_db
 *   3. Rank by disease match + age + state + funding capacity
 *   4. Admin manually sends email to top 3 NGOs
 *   5. Track response - ACCEPTED / REJECTED
 *   6. Patient analytics shows NGO status
 *   7. On hospital change -> notify all matched NGOs immediately
 */

const express    = require('express');
const router     = express.Router();
const axios      = require('axios');
const mysql      = require('mysql2/promise');
const prisma     = require('../utils/prisma');
const nodemailer = require('nodemailer');
const crypto     = require('crypto');
const { verifyToken, verifyAdmin } = require('../middleware/auth');

// ─────────────────────────────────────────────────────────────
// NGO DB CONNECTION - separate ngo_db MySQL database
// ─────────────────────────────────────────────────────────────
let ngoPool = null;

const getNgoPool = () => {
  if (!ngoPool) {
    ngoPool = mysql.createPool({
      host              : process.env.NGO_DB_HOST     || 'localhost',
      user              : process.env.NGO_DB_USER     || 'root',
      password          : process.env.NGO_DB_PASSWORD || '',
      database          : process.env.NGO_DB_NAME     || 'ngo_db',
      waitForConnections: true,
      connectionLimit   : 10,
    });
  }
  return ngoPool;
};

// ─────────────────────────────────────────────────────────────
// HELPER - Map disease text to ngo_db column
// ─────────────────────────────────────────────────────────────
const mapDiseaseToColumn = (diseaseText) => {
  if (!diseaseText) return 'disease_general';

  const text = diseaseText.toLowerCase();

  const categoryMap = {
    disease_cardiac: [
      'coronary','cardiac','heart','cabg','bypass','angioplasty',
      'myocardial','infarction','vessel','artery','stent','valve',
      'pacemaker','angina','cardiomyopathy','arrhythmia','open heart',
      'heart failure','atrial','ventricular','aorta',
    ],
    disease_cancer: [
      'cancer','tumor','tumour','carcinoma','lymphoma','leukemia',
      'leukaemia','chemotherapy','oncology','malignant','sarcoma',
      'melanoma','biopsy','metastasis','radiation','radiotherapy',
    ],
    disease_neuro: [
      'neuro','brain','stroke','paralysis','epilepsy','seizure',
      'parkinson','alzheimer','dementia','spinal','spine','migraine',
      'cerebral','nervous','multiple sclerosis','neuropathy','head injury',
    ],
    disease_kidney: [
      'kidney','renal','dialysis','nephro','urinary','bladder',
      'nephrotic','nephritis','ckd','chronic kidney','kidney failure',
      'kidney stone',
    ],
    disease_liver: [
      'liver','hepatic','hepatitis','cirrhosis','jaundice',
      'gallbladder','bile','fatty liver','fibrosis','liver failure',
      'liver transplant',
    ],
    disease_orthopedic: [
      'bone','fracture','orthopedic','joint','knee','hip',
      'replacement','disc','ligament','tendon','osteoporosis',
      'arthritis','scoliosis','spinal cord','vertebra',
    ],
    disease_eye: [
      'eye','vision','retina','cataract','glaucoma','cornea',
      'optic','blindness','ocular','vitreous','macular',
      'diabetic retinopathy',
    ],
    disease_rare: [
      'rare','genetic','muscular dystrophy','thalassemia',
      'hemophilia','down syndrome','wilson','gaucher','fabry',
      'pompe','hunter syndrome','cystic fibrosis','sickle cell',
    ],
  };

  for (const [column, keywords] of Object.entries(categoryMap)) {
    for (const keyword of keywords) {
      if (text.includes(keyword)) return column;
    }
  }

  return 'disease_general';
};

// ─────────────────────────────────────────────────────────────
// HELPER - Map age to ngo_db age column
// ─────────────────────────────────────────────────────────────
const mapAgeToColumn = (age) => {
  if (!age)      return 'supports_adults';
  if (age < 18)  return 'supports_children';
  if (age >= 60) return 'supports_elderly';
  return 'supports_adults';
};

// ─────────────────────────────────────────────────────────────
// HELPER - Notify Flask service
// ─────────────────────────────────────────────────────────────
const notifyFlask = async (path, data) => {
  try {
    await axios.post(
      process.env.FLASK_BASE_URL + path,
      data,
      {
        headers: { 'x-flask-secret': process.env.FLASK_INTERNAL_SECRET },
        timeout: 10000,
      }
    );
  } catch (err) {
    console.log('Flask notification failed ' + path + ':', err.message);
  }
};

// ─────────────────────────────────────────────────────────────
// HELPER - Build NGO email HTML (no template literals)
// ─────────────────────────────────────────────────────────────
const buildEmailHTML = (ngoName, campaign, acceptUrl, rejectUrl) => {
  const patientName   = campaign.patient_full_name || 'Patient';
  const campaignTitle = campaign.title             || 'Medical Campaign';
  const disease       = (campaign.fund_needer && campaign.fund_needer.disease) || 'N/A';
  const amount        = campaign.verified_amount || campaign.goal_amount || 0;

  return (
    '<!DOCTYPE html>' +
    '<html><head><meta charset="UTF-8">' +
    '<style>' +
    'body{font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:20px}' +
    '.card{background:#fff;border-radius:8px;padding:30px;max-width:600px;margin:auto}' +
    'h2{color:#2c3e50}' +
    '.btn{display:inline-block;padding:12px 28px;border-radius:6px;' +
    'text-decoration:none;color:#fff;font-weight:bold;margin:8px}' +
    '.accept{background:#27ae60}.reject{background:#e74c3c}' +
    '.info{background:#f8f9fa;border-left:4px solid #3498db;padding:12px;margin:16px 0}' +
    'small{color:#888}' +
    '</style></head><body>' +
    '<div class="card">' +
    '<h2>MediTrust - NGO Support Request</h2>' +
    '<p>Dear <strong>' + ngoName + '</strong>,</p>' +
    '<p>A patient on the MediTrust platform requires financial assistance. ' +
    'Based on your organisation profile, you have been selected as a potential support partner.</p>' +
    '<div class="info">' +
    '<strong>Campaign:</strong> ' + campaignTitle + '<br>' +
    '<strong>Patient:</strong> '  + patientName   + '<br>' +
    '<strong>Disease:</strong> '  + disease        + '<br>' +
    '<strong>Amount Needed:</strong> Rs. ' + Number(amount).toLocaleString('en-IN') +
    '</div>' +
    '<p><strong>📎 Supporting Documents:</strong> Patient medical records, verification documents, and hospital reports are attached to this email for your review.</p>' +
    '<p>Please review the documents and respond:</p>' +
    '<a href="' + acceptUrl + '" class="btn accept">Accept and Support</a>' +
    '&nbsp;' +
    '<a href="' + rejectUrl + '" class="btn reject">Unable to Support</a>' +
    '<p><small>This link expires in 7 days. If you did not expect this email, please ignore it.</small></p>' +
    '</div>' +
    '</body></html>'
  );
};

// ─────────────────────────────────────────────────────────────
// TEST
// GET /api/ngo/test
// ─────────────────────────────────────────────────────────────
router.get('/test', (_req, res) => {
  res.json({ success: true, message: 'NGO routes working!' });
});

// ─────────────────────────────────────────────────────────────
// MATCH NGOs - Core matching algorithm
// POST /api/ngo/match/:campaign_id
// Auth: patient token OR internal Flask secret
// ─────────────────────────────────────────────────────────────
router.post('/match/:campaign_id', async (req, res) => {
  const authHeader     = req.headers['authorization'];
  const internalSecret = req.headers['x-flask-secret'];

  if (!authHeader && internalSecret !== process.env.FLASK_INTERNAL_SECRET) {
    return res.status(401).json({ success: false, error: 'Unauthorized' });
  }

  if (authHeader) {
    try {
      const token = authHeader.split(' ')[1];
      const jwt   = require('jsonwebtoken');
      req.user    = jwt.verify(token, process.env.JWT_SECRET);
    } catch {
      return res.status(401).json({ success: false, error: 'Invalid token' });
    }
  }

  try {
    const campaignId = parseInt(req.params.campaign_id);

    const campaign = await prisma.campaign.findUnique({
      where  : { id: campaignId },
      include: {
        patient : { select: { email: true, name: true } },
        hospital: true,
      },
    });

    if (!campaign) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    if (req.user && campaign.patient_id !== req.user.id) {
      return res.status(403).json({ success: false, error: 'Unauthorized' });
    }

    if (!['LIVE_CAMPAIGN', 'LIVE_UPDATED'].includes(campaign.status)) {
      return res.status(400).json({
        success: false,
        error  : 'NGO matching only available for live campaigns',
      });
    }

    const diseaseText   = req.body.disease || campaign.title;
    const patientAge    = campaign.patient_age;
    const patientState  = campaign.patient_state;
    const diseaseColumn = mapDiseaseToColumn(diseaseText);
    const ageColumn     = mapAgeToColumn(patientAge);

    console.log('\nNGO Matching for Campaign ' + campaignId);
    console.log('   Disease Column : ' + diseaseColumn);
    console.log('   Age Column     : ' + ageColumn);
    console.log('   Patient State  : ' + patientState);

    const pool = getNgoPool();

    const [ngos] = await pool.execute(
      'SELECT' +
      '  i.ngo_id, i.ngo_name, i.contact_email, i.phone_number,' +
      '  i.alternate_phone, i.headquarters_city, i.state,' +
      '  i.website_url, i.registration_number,' +
      '  m.' + diseaseColumn + ' AS disease_match,' +
      '  m.' + ageColumn     + ' AS age_match,' +
      '  m.disease_general,' +
      '  f.max_grant_per_patient_inr, f.avg_grant_per_patient_inr,' +
      '  f.annual_budget_range, f.csr_connected, f.government_support,' +
      '  f.registration_80G,' +
      '  e.income_eligibility_max_inr, e.online_application_available,' +
      '  e.processing_time_days,' +
      '  s.geographic_scope, s.primary_state, s.hospital_partnership_known' +
      ' FROM ngo_identity i' +
      ' JOIN ngo_medical_capability m      ON i.ngo_id = m.ngo_id' +
      ' JOIN ngo_funding_capacity f        ON i.ngo_id = f.ngo_id' +
      ' JOIN ngo_eligibility_application e ON i.ngo_id = e.ngo_id' +
      ' JOIN ngo_system_info s             ON i.ngo_id = s.ngo_id' +
      ' WHERE i.contact_email IS NOT NULL' +
      '   AND (m.' + diseaseColumn + ' = 1 OR m.disease_general = 1)' +
      '   AND m.' + ageColumn + ' = 1'
    );

    if (ngos.length === 0) {
      return res.json({
        success: true,
        message: 'No matching NGOs found for this case',
        matched: 0,
        ngos   : [],
      });
    }

    const ranked = ngos.map((ngo) => {
      let score = 0;

      if (ngo.disease_match)        score += 40;
      else if (ngo.disease_general) score += 10;

      if (ngo.primary_state && patientState &&
          ngo.primary_state.toLowerCase().includes(patientState.toLowerCase())) {
        score += 25;
      }

      if (ngo.geographic_scope === 'National')  score += 15;
      else if (ngo.geographic_scope === 'State')    score += 10;
      else if (ngo.geographic_scope === 'Regional') score += 5;

      const maxGrant = parseFloat(ngo.max_grant_per_patient_inr || 0);
      const needed   = parseFloat(campaign.verified_amount       || 0);
      if (maxGrant >= needed) score += 20;
      else if (maxGrant > 0)  score += 10;

      if (ngo.hospital_partnership_known === 'Yes') score += 10;
      if (ngo.online_application_available)          score += 5;
      if (ngo.csr_connected)                         score += 5;
      if (ngo.government_support)                    score += 5;

      return Object.assign({}, ngo, { match_score: score });
    });

    const top3 = ranked
      .sort((a, b) => b.match_score - a.match_score)
      .slice(0, 3);

    console.log('   Found ' + ngos.length + ' NGOs, selected top ' + top3.length);

    const savedMatches = [];

    for (const ngo of top3) {
      const existing = await prisma.nGOMatch.findFirst({
        where: { campaign_id: campaignId, ngo_id: ngo.ngo_id },
      });

      if (!existing) {
        const match = await prisma.nGOMatch.create({
          data: {
            campaign_id: campaignId,
            ngo_id     : ngo.ngo_id,
            status     : 'PENDING',
          },
        });

        savedMatches.push({
          match_id : match.id,
          ngo_id   : ngo.ngo_id,
          ngo_name : ngo.ngo_name,
          email    : ngo.contact_email,
          city     : ngo.headquarters_city,
          state    : ngo.state,
          score    : ngo.match_score,
          max_grant: ngo.max_grant_per_patient_inr,
        });

        console.log('   Matched: ' + ngo.ngo_name + ' (PENDING)');
      } else {
        console.log('   Already matched: ' + ngo.ngo_name);
      }
    }

    await prisma.adminAuditLog.create({
      data: {
        admin_id   : (req.user && req.user.id) || 1,
        action     : 'NGO_MATCHED',
        target_type: 'campaign',
        target_id  : campaignId,
        notes      : 'Matched ' + savedMatches.length + ' NGOs for campaign ' + campaignId,
      },
    }).catch(() => {});

    res.json({
      success        : true,
      message        : savedMatches.length + ' NGOs matched successfully',
      matched        : savedMatches.length,
      disease_matched: diseaseColumn,
      ngos           : savedMatches,
    });

  } catch (error) {
    console.error('NGO match error:', error);
    res.status(500).json({ success: false, error: 'NGO matching failed: ' + error.message });
  }
});

// ─────────────────────────────────────────────────────────────
// ADMIN SENDS EMAIL TO NGO MANUALLY
// POST /api/ngo/send-email/:match_id
// Auth: admin token
// ─────────────────────────────────────────────────────────────
router.post('/send-email/:match_id', verifyAdmin, async (req, res) => {
  try {
    const matchId = parseInt(req.params.match_id);
    const { email_subject, email_body } = req.body;

    const match = await prisma.nGOMatch.findUnique({
      where  : { id: matchId },
      include: {
        campaign: {
          include: {
            patient    : { select: { name: true, email: true } },
            fund_needer: true,
            documents  : true,
          },
        },
      },
    });

    if (!match) {
      return res.status(404).json({ success: false, error: 'Match not found' });
    }

    const pool   = getNgoPool();
    const [rows] = await pool.execute(
      'SELECT ngo_name, contact_email FROM ngo_identity WHERE ngo_id = ?',
      [match.ngo_id]
    );

    if (!rows.length || !rows[0].contact_email) {
      return res.status(404).json({ success: false, error: 'NGO email not found' });
    }

    const ngo = rows[0];

    // Generate token for accept/reject links (valid 7 days)
    const token   = crypto.randomBytes(32).toString('hex');
    const expires = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);

    await prisma.nGOMatch.update({
      where: { id: matchId },
      data : {
        response_token     : token,
        response_expires_at: expires,
        status             : 'NOTIFIED',
        notified_at        : new Date(),
      },
    });

    const BASE_URL  = process.env.BACKEND_URL || 'http://localhost:3000';
    const acceptUrl = BASE_URL + '/api/ngo/respond?token=' + token + '&status=ACCEPTED';
    const rejectUrl = BASE_URL + '/api/ngo/respond?token=' + token + '&status=REJECTED';

    // Always include response links, even with custom email body
    const responseLinksHTML = 
      '<hr style="margin:30px 0;border:none;border-top:1px solid #eee">' +
      '<div style="text-align:center;padding:20px;background:#f8f9fa;border-radius:8px">' +
      '<h3 style="color:#2c3e50;margin-bottom:15px">Please Respond to This Request</h3>' +
      '<p style="color:#555;margin-bottom:20px">Your response helps us coordinate support for this patient.</p>' +
      '<a href="' + acceptUrl + '" style="display:inline-block;padding:12px 28px;background:#27ae60;color:#fff;text-decoration:none;border-radius:6px;font-weight:bold;margin:0 8px">✅ Accept and Support</a>' +
      '<a href="' + rejectUrl + '" style="display:inline-block;padding:12px 28px;background:#e74c3c;color:#fff;text-decoration:none;border-radius:6px;font-weight:bold;margin:0 8px">❌ Unable to Support</a>' +
      '<p style="color:#888;font-size:12px;margin-top:20px">This link expires in 7 days. If you did not expect this email, please ignore it.</p>' +
      '</div>';

    const htmlContent = email_body
      ? email_body.replace(/\n/g, '<br>') + responseLinksHTML
      : buildEmailHTML(ngo.ngo_name, match.campaign, acceptUrl, rejectUrl);

    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: process.env.EMAIL_USER,
        pass: process.env.EMAIL_APP_PASSWORD,
      },
    });

    // Prepare email attachments from campaign documents
    const attachments = [];
    if (match.campaign.documents && match.campaign.documents.length > 0) {
      for (const doc of match.campaign.documents) {
        // Extract base64 data from data URL if present
        if (doc.file_url && doc.file_url.startsWith('data:')) {
          const matches = doc.file_url.match(/^data:([^;]+);base64,(.+)$/);
          if (matches) {
            attachments.push({
              filename: doc.file_name || 'document.pdf',
              content: Buffer.from(matches[2], 'base64'),
              contentType: matches[1]
            });
          }
        }
      }
    }

    const mailOptions = {
      from   : 'MediTrust Platform <' + process.env.EMAIL_USER + '>',
      to     : ngo.contact_email,
      subject: email_subject || 'MediTrust - NGO Support Request',
      html   : htmlContent,
    };

    // Add attachments if any documents exist
    if (attachments.length > 0) {
      mailOptions.attachments = attachments;
      console.log('Attaching', attachments.length, 'documents to NGO email');
    }

    await transporter.sendMail(mailOptions);

    await prisma.adminAuditLog.create({
      data: {
        admin_id   : req.admin.id,
        action     : 'NGO_EMAIL_SENT',
        target_type: 'ngo_match',
        target_id  : matchId,
        notes      : 'Email sent to ' + ngo.ngo_name + ' <' + ngo.contact_email + '>',
      },
    });

    res.json({
      success  : true,
      message  : 'Email sent to ' + ngo.ngo_name,
      ngo_email: ngo.contact_email,
    });

  } catch (err) {
    console.error('Send NGO email error:', err);
    res.status(500).json({ success: false, error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────
// NGO RESPONDS VIA EMAIL LINK
// Shared handler - used by GET (browser link) and POST (API)
// ─────────────────────────────────────────────────────────────
async function handleNGORespond(token, status, res) {
  if (!token) {
    return res.status(400).json({ success: false, error: 'Response token is required' });
  }
  if (!['ACCEPTED', 'REJECTED'].includes(status)) {
    return res.status(400).json({ success: false, error: 'Status must be ACCEPTED or REJECTED' });
  }

  const match = await prisma.nGOMatch.findFirst({
    where: {
      response_token     : token,
      response_expires_at: { gt: new Date() },
    },
    include: { campaign: { include: { fund_needer: true } } },
  });

  if (!match) {
    return res.status(404).send(
      '<html><body style="font-family:Arial;text-align:center;padding:60px">' +
      '<h2 style="color:#e74c3c">Invalid or Expired Link</h2>' +
      '<p>This response link has already been used or has expired.</p>' +
      '<p>Please contact MediTrust if you need to update your response.</p>' +
      '</body></html>'
    );
  }

  if (!['PENDING', 'NOTIFIED'].includes(match.status)) {
    return res.status(409).send(
      '<html><body style="font-family:Arial;text-align:center;padding:60px">' +
      '<h2 style="color:#e67e22">Already Responded</h2>' +
      '<p>You have already responded to this request (Status: ' + match.status + ').</p>' +
      '</body></html>'
    );
  }

  await prisma.nGOMatch.update({
    where: { id: match.id },
    data : {
      status             : status,
      responded_at       : new Date(),
      response_token     : null,
      response_expires_at: null,
    },
  });

  await prisma.adminAuditLog.create({
    data: {
      admin_id   : 1,
      action     : 'NGO_RESPONDED_' + status,
      target_type: 'ngo_match',
      target_id  : match.id,
      notes      : 'NGO responded ' + status + ' via email link',
    },
  });

  const color   = status === 'ACCEPTED' ? '#27ae60' : '#e74c3c';
  const icon    = status === 'ACCEPTED' ? '&#10004;' : '&#10008;';
  const heading = status === 'ACCEPTED' ? 'Thank You for Accepting!' : 'Response Recorded';
  const body    = status === 'ACCEPTED'
    ? 'Thank you! Our team will contact you shortly to coordinate fund disbursement.'
    : 'We appreciate your response. We will explore other support options for this patient.';

  return res.send(
    '<html><body style="font-family:Arial;text-align:center;padding:60px;background:#f4f4f4">' +
    '<div style="background:#fff;border-radius:10px;padding:40px;max-width:480px;margin:auto">' +
    '<div style="font-size:56px">' + icon + '</div>' +
    '<h2 style="color:' + color + '">' + heading + '</h2>' +
    '<p style="color:#555">' + body + '</p>' +
    '<p style="color:#aaa;font-size:12px">MediTrust Platform</p>' +
    '</div>' +
    '</body></html>'
  );
}

// GET - NGO clicks link in email (browser)
router.get('/respond', async (req, res) => {
  try {
    await handleNGORespond(req.query.token, req.query.status, res);
  } catch (error) {
    console.error('NGO respond GET error:', error);
    res.status(500).send('<h2>Something went wrong. Please try again.</h2>');
  }
});

// POST - programmatic / API call
router.post('/respond', async (req, res) => {
  try {
    await handleNGORespond(req.body.token, req.body.status, res);
  } catch (error) {
    console.error('NGO respond POST error:', error);
    res.status(500).json({ success: false, error: 'Failed to record NGO response' });
  }
});

// ─────────────────────────────────────────────────────────────
// PATIENT - VIEW NGO MATCHES FOR THEIR CAMPAIGN
// GET /api/ngo/campaign/:campaign_id
// Auth: patient token
// ─────────────────────────────────────────────────────────────
router.get('/campaign/:campaign_id', verifyToken, async (req, res) => {
  try {
    const campaignId = parseInt(req.params.campaign_id);

    const campaign = await prisma.campaign.findUnique({
      where: { id: campaignId },
    });

    if (!campaign || campaign.patient_id !== req.user.id) {
      return res.status(403).json({ success: false, error: 'Unauthorized' });
    }

    const matches = await prisma.nGOMatch.findMany({
      where  : { campaign_id: campaignId },
      orderBy: { notified_at: 'desc' },
    });

    const pool     = getNgoPool();
    const enriched = await Promise.all(
      matches.map(async (match) => {
        try {
          const [rows] = await pool.execute(
            'SELECT i.ngo_name, i.headquarters_city, i.state, i.website_url,' +
            '  i.phone_number, f.max_grant_per_patient_inr' +
            ' FROM ngo_identity i' +
            ' JOIN ngo_funding_capacity f ON i.ngo_id = f.ngo_id' +
            ' WHERE i.ngo_id = ?',
            [match.ngo_id]
          );
          return {
            match_id    : match.id,
            ngo_id      : match.ngo_id,
            ngo_name    : (rows[0] && rows[0].ngo_name)                 || 'Unknown NGO',
            city        : (rows[0] && rows[0].headquarters_city)        || '',
            state       : (rows[0] && rows[0].state)                    || '',
            website     : (rows[0] && rows[0].website_url)              || '',
            phone       : (rows[0] && rows[0].phone_number)             || '',
            max_grant   : (rows[0] && rows[0].max_grant_per_patient_inr)|| 0,
            status      : match.status,
            notified_at : match.notified_at,
            responded_at: match.responded_at,
          };
        } catch (_) {
          return {
            match_id    : match.id,
            ngo_id      : match.ngo_id,
            ngo_name    : 'NGO',
            status      : match.status,
            notified_at : match.notified_at,
            responded_at: match.responded_at,
          };
        }
      })
    );

    const summary = {
      total_notified: matches.length,
      accepted      : matches.filter((m) => m.status === 'ACCEPTED').length,
      rejected      : matches.filter((m) => m.status === 'REJECTED').length,
      pending       : matches.filter((m) => m.status === 'NOTIFIED' || m.status === 'PENDING').length,
    };

    res.json({ success: true, summary, matches: enriched });

  } catch (error) {
    console.error('Get NGO matches error:', error);
    res.status(500).json({ success: false, error: 'Failed to get NGO matches' });
  }
});

// ─────────────────────────────────────────────────────────────
// ADMIN - ALL NGO MATCHES (dashboard table)
// GET /api/ngo/all-matches
// Auth: admin token
// ─────────────────────────────────────────────────────────────
router.get('/all-matches', verifyAdmin, async (req, res) => {
  try {
    const matches = await prisma.nGOMatch.findMany({
      include: {
        campaign: {
          select: {
            id               : true,
            title            : true,
            patient_full_name: true,
            status           : true,
          },
        },
      },
      orderBy: { id: 'desc' },
      take   : 100,
    });

    const pool     = getNgoPool();
    const enriched = await Promise.all(
      matches.map(async (match) => {
        try {
          const [rows] = await pool.execute(
            'SELECT i.ngo_name, i.contact_email, i.headquarters_city, i.state,' +
            '  i.phone_number, f.max_grant_per_patient_inr' +
            ' FROM ngo_identity i' +
            ' JOIN ngo_funding_capacity f ON i.ngo_id = f.ngo_id' +
            ' WHERE i.ngo_id = ?',
            [match.ngo_id]
          );
          return Object.assign({}, match, {
            ngo_name : (rows[0] && rows[0].ngo_name)                 || 'Unknown NGO',
            ngo_email: (rows[0] && rows[0].contact_email)            || '',
            city     : (rows[0] && rows[0].headquarters_city)        || '',
            state    : (rows[0] && rows[0].state)                    || '',
            phone    : (rows[0] && rows[0].phone_number)             || '',
            max_grant: (rows[0] && rows[0].max_grant_per_patient_inr)|| 0,
          });
        } catch (_) {
          return Object.assign({}, match, {
            ngo_name : 'NGO',
            ngo_email: '',
            city     : '',
            state    : '',
            phone    : '',
            max_grant: 0,
          });
        }
      })
    );

    const summary = {
      total   : matches.length,
      accepted: matches.filter((m) => m.status === 'ACCEPTED').length,
      rejected: matches.filter((m) => m.status === 'REJECTED').length,
      notified: matches.filter((m) => m.status === 'NOTIFIED').length,
      pending : matches.filter((m) => m.status === 'PENDING').length,
    };

    res.json({ success: true, summary, matches: enriched });

  } catch (error) {
    console.error('Get all NGO matches error:', error);
    res.status(500).json({ success: false, error: 'Failed to get NGO matches', detail: error.message });
  }
});

// ─────────────────────────────────────────────────────────────
// ADMIN - MATCH DETAIL MODAL
// GET /api/ngo/match-detail/:match_id
// Auth: admin token
// ─────────────────────────────────────────────────────────────
router.get('/match-detail/:match_id', verifyAdmin, async (req, res) => {
  try {
    const match = await prisma.nGOMatch.findUnique({
      where  : { id: parseInt(req.params.match_id) },
      include: {
        campaign: {
          include: {
            documents  : { select: { id: true, document_type: true, file_name: true } },
            fund_needer: true,
            patient    : { select: { name: true, email: true } },
          },
        },
      },
    });

    if (!match) {
      return res.status(404).json({ success: false, error: 'Match not found' });
    }

    const pool   = getNgoPool();
    const [rows] = await pool.execute(
      'SELECT i.ngo_name, i.contact_email, i.phone_number,' +
      '  i.headquarters_city, i.state, i.website_url,' +
      '  f.max_grant_per_patient_inr' +
      ' FROM ngo_identity i' +
      ' JOIN ngo_funding_capacity f ON i.ngo_id = f.ngo_id' +
      ' WHERE i.ngo_id = ?',
      [match.ngo_id]
    );

    res.json({
      success: true,
      match  : {
        id          : match.id,
        status      : match.status,
        notified_at : match.notified_at,
        responded_at: match.responded_at,
        ngo         : rows[0] || null,
        campaign    : {
          id             : match.campaign.id,
          title          : match.campaign.title,
          patient_name   : match.campaign.patient_full_name,
          patient_city   : match.campaign.patient_city,
          disease        : (match.campaign.fund_needer && match.campaign.fund_needer.disease)       || '',
          hospital       : (match.campaign.fund_needer && match.campaign.fund_needer.hospital_name) || '',
          verified_amount: match.campaign.verified_amount,
          documents      : match.campaign.documents,
        },
      },
    });

  } catch (err) {
    console.error('Match detail error:', err);
    res.status(500).json({ success: false, error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────
// ADMIN - SEARCH NGO DB
// GET /api/ngo/search?disease=cardiac&state=Telangana&age=30
// Auth: admin token
// ─────────────────────────────────────────────────────────────
router.get('/search', verifyAdmin, async (req, res) => {
  try {
    const { disease, state, age } = req.query;

    const diseaseColumn = disease ? mapDiseaseToColumn(disease)   : 'disease_general';
    const ageColumn     = age     ? mapAgeToColumn(parseInt(age)) : 'supports_adults';

    const pool  = getNgoPool();
    let   query =
      'SELECT i.ngo_id, i.ngo_name, i.contact_email, i.phone_number,' +
      '  i.headquarters_city, i.state, i.website_url,' +
      '  f.max_grant_per_patient_inr, f.annual_budget_range,' +
      '  s.geographic_scope, s.primary_state,' +
      '  s.hospital_partnership_known,' +
      '  e.online_application_available, e.processing_time_days' +
      ' FROM ngo_identity i' +
      ' JOIN ngo_medical_capability m      ON i.ngo_id = m.ngo_id' +
      ' JOIN ngo_funding_capacity f        ON i.ngo_id = f.ngo_id' +
      ' JOIN ngo_system_info s             ON i.ngo_id = s.ngo_id' +
      ' JOIN ngo_eligibility_application e ON i.ngo_id = e.ngo_id' +
      ' WHERE (m.' + diseaseColumn + ' = 1 OR m.disease_general = 1)' +
      '   AND m.' + ageColumn + ' = 1';

    const params = [];
    if (state) {
      query += " AND (s.primary_state LIKE ? OR s.geographic_scope = 'National')";
      params.push('%' + state + '%');
    }

    query += ' ORDER BY f.max_grant_per_patient_inr DESC LIMIT 20';

    const [ngos] = await pool.execute(query, params);

    res.json({ success: true, count: ngos.length, ngos });

  } catch (error) {
    console.error('NGO search error:', error);
    res.status(500).json({ success: false, error: 'NGO search failed: ' + error.message });
  }
});

// ─────────────────────────────────────────────────────────────
// NOTIFY NGOs ON HOSPITAL CHANGE
// POST /api/ngo/notify-hospital-change/:campaign_id
// Auth: patient token
// ─────────────────────────────────────────────────────────────
router.post('/notify-hospital-change/:campaign_id', verifyToken, async (req, res) => {
  try {
    const campaignId                     = parseInt(req.params.campaign_id);
    const { old_hospital, new_hospital } = req.body;

    const campaign = await prisma.campaign.findUnique({
      where: { id: campaignId },
    });

    if (!campaign || campaign.patient_id !== req.user.id) {
      return res.status(403).json({ success: false, error: 'Unauthorized' });
    }

    const matches = await prisma.nGOMatch.findMany({
      where: { campaign_id: campaignId },
    });

    if (matches.length === 0) {
      return res.json({ success: true, message: 'No NGOs to notify', notified: 0 });
    }

    const pool = getNgoPool();
    let   notifiedCount = 0;

    for (const match of matches) {
      try {
        const [rows] = await pool.execute(
          'SELECT ngo_name, contact_email FROM ngo_identity WHERE ngo_id = ?',
          [match.ngo_id]
        );

        if (rows[0] && rows[0].contact_email) {
          await notifyFlask('/notify/hospital-change', {
            to_email      : rows[0].contact_email,
            ngo_name      : rows[0].ngo_name,
            campaign_title: campaign.title,
            patient_name  : campaign.patient_full_name,
            old_hospital  : old_hospital || 'Previous Hospital',
            new_hospital  : new_hospital || 'New Hospital',
          });
          notifiedCount++;
        }
      } catch (err) {
        console.log('Failed to notify NGO ' + match.ngo_id + ':', err.message);
      }
    }

    res.json({
      success : true,
      message : notifiedCount + ' NGOs notified of hospital change',
      notified: notifiedCount,
    });

  } catch (error) {
    console.error('NGO hospital change notify error:', error);
    res.status(500).json({ success: false, error: 'Failed to notify NGOs' });
  }
});

module.exports = router;