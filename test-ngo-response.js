/**
 * MediTrust — NGO Matching & Response System
 * Complete fixed version — all endpoints included
 */

const express    = require('express');
const router     = express.Router();
const prisma     = require('../utils/prisma');
const nodemailer = require('nodemailer');
const crypto     = require('crypto');

// ─────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────

/** Verify admin JWT */
function verifyAdmin(req, res) {
  try {
    const authHeader = req.headers.authorization || '';
    const token = authHeader.replace('Bearer ', '');
    if (!token) {
      res.status(401).json({ success: false, error: 'Admin token required' });
      return null;
    }
    const jwt = require('jsonwebtoken');
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    if (decoded.role !== 'admin') {
      res.status(403).json({ success: false, error: 'Admin access only' });
      return null;
    }
    return decoded;
  } catch {
    res.status(401).json({ success: false, error: 'Invalid admin token' });
    return null;
  }
}

/** Verify patient JWT */
function verifyPatient(req, res) {
  try {
    const authHeader = req.headers.authorization || '';
    const token = authHeader.replace('Bearer ', '');
    if (!token) {
      res.status(401).json({ success: false, error: 'Auth token required' });
      return null;
    }
    const jwt = require('jsonwebtoken');
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    return decoded;
  } catch {
    res.status(401).json({ success: false, error: 'Invalid token' });
    return null;
  }
}

/** Build nodemailer transporter */
function getTransporter() {
  return nodemailer.createTransport({
    host:   process.env.SMTP_HOST   || 'smtp.gmail.com',
    port:   parseInt(process.env.SMTP_PORT || '587'),
    secure: false,
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS,
    },
  });
}

/** Simple HTML email for NGO accept/reject */
function buildEmailHTML(ngo, campaign, acceptUrl, rejectUrl) {
  const patientName = campaign.fund_needer
    ? (campaign.fund_needer.full_name || 'Patient')
    : 'Patient';

  return [
    '<!DOCTYPE html>',
    '<html><head><meta charset="UTF-8">',
    '<style>',
    'body{font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:20px}',
    '.card{background:#fff;border-radius:8px;padding:30px;max-width:600px;margin:auto}',
    'h2{color:#2c3e50}',
    '.btn{display:inline-block;padding:12px 28px;border-radius:6px;',
    '     text-decoration:none;color:#fff;font-weight:bold;margin:8px}',
    '.accept{background:#27ae60}.reject{background:#e74c3c}',
    '.info{background:#f8f9fa;border-left:4px solid #3498db;padding:12px;margin:16px 0}',
    'small{color:#888}',
    '</style></head><body>',
    '<div class="card">',
    '<h2>MediTrust — NGO Support Request</h2>',
    '<p>Dear <strong>' + (ngo.name || 'NGO Partner') + '</strong>,</p>',
    '<p>A patient on the MediTrust platform needs financial assistance.',
    ' Based on your organisation\'s profile, you have been identified as a potential support partner.</p>',
    '<div class="info">',
    '<strong>Campaign:</strong> ' + (campaign.title || 'Medical Campaign') + '<br>',
    '<strong>Patient:</strong> ' + patientName + '<br>',
    '<strong>Disease:</strong> ' + (campaign.disease || 'N/A') + '<br>',
    '<strong>Amount Needed:</strong> ₹' + (campaign.goal_amount || 0).toLocaleString(),
    '</div>',
    '<p>Please review and respond below:</p>',
    '<a href="' + acceptUrl + '" class="btn accept">✔ Accept &amp; Support</a>',
    '<a href="' + rejectUrl + '" class="btn reject">✘ Unable to Support</a>',
    '<p><small>This link expires in 7 days. If you did not expect this email, please ignore it.</small></p>',
    '</div>',
    '</body></html>',
  ].join('\n');
}

// ─────────────────────────────────────────
// 1. TEST
// GET /api/ngo/test
// ─────────────────────────────────────────
router.get('/test', (_req, res) => {
  res.json({ success: true, message: 'NGO routes working!' });
});

// ─────────────────────────────────────────
// 2. MATCH NGOs FOR A CAMPAIGN
// POST /api/ngo/match/:campaign_id
// Auth: patient token OR internal Flask secret
// ─────────────────────────────────────────
router.post('/match/:campaign_id', async (req, res) => {
  try {
    const campaignId = parseInt(req.params.campaign_id);

    // Accept internal Flask call via secret header
    const internalSecret = req.headers['x-internal-secret'];
    const isInternal = internalSecret && internalSecret === process.env.FLASK_INTERNAL_SECRET;

    if (!isInternal) {
      const user = verifyPatient(req, res);
      if (!user) return;
    }

    // Fetch campaign
    const campaign = await prisma.campaign.findUnique({
      where: { id: campaignId },
      include: { fund_needer: true },
    });

    if (!campaign) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    // Disease → column mapping
    const diseaseMap = {
      cardiac: ['cardiac', 'heart', 'cardio'],
      cancer:  ['cancer', 'oncology', 'tumor', 'tumour'],
      neuro:   ['neuro', 'brain', 'neurological', 'epilepsy'],
      ortho:   ['ortho', 'bone', 'fracture', 'joint'],
      renal:   ['renal', 'kidney', 'dialysis'],
      liver:   ['liver', 'hepatic', 'hepatitis'],
      general: [],
    };

    const diseaseLower = (campaign.disease || '').toLowerCase();
    let matchedDiseaseCol = 'general';
    for (const [col, keywords] of Object.entries(diseaseMap)) {
      if (keywords.some(k => diseaseLower.includes(k))) {
        matchedDiseaseCol = col;
        break;
      }
    }

    // Age → column mapping
    const patientAge = campaign.fund_needer?.age || 30;
    let ageCol = 'adults';
    if (patientAge < 18) ageCol = 'children';
    else if (patientAge >= 60) ageCol = 'elderly';

    // Query NGO DB for matching NGOs
    // Adjust table/column names to match your actual ngo_db schema
    const ngos = await prisma.$queryRawUnsafe(`
      SELECT
        ni.id,
        ni.name,
        ni.email,
        ni.state,
        nmc.${matchedDiseaseCol}  AS disease_support,
        nfc.max_grant_amount,
        nsi.geographic_scope
      FROM ngo_identity ni
      LEFT JOIN ngo_medical_capability nmc ON nmc.ngo_id = ni.id
      LEFT JOIN ngo_funding_capacity   nfc ON nfc.ngo_id = ni.id
      LEFT JOIN ngo_system_info        nsi ON nsi.ngo_id = ni.id
      WHERE nmc.${matchedDiseaseCol} = true
        AND (nsi.geographic_scope = 'national'
             OR nsi.state = '${(campaign.state || '').replace(/'/g, "''")}')
      LIMIT 20
    `);

    if (!ngos || ngos.length === 0) {
      return res.json({
        success: true,
        message: 'No matching NGOs found for this campaign',
        matches: [],
      });
    }

    // Score: disease match (10) + same state (5) + grant capacity
    const campaignGoal = Number(campaign.goal_amount) || 0;
    const scored = ngos.map(ngo => {
      let score = 0;
      if (ngo.disease_support) score += 10;
      if ((ngo.state || '').toLowerCase() === (campaign.state || '').toLowerCase()) score += 5;
      const grant = Number(ngo.max_grant_amount) || 0;
      if (grant >= campaignGoal) score += 5;
      else if (grant >= campaignGoal * 0.5) score += 2;
      return { ...ngo, score };
    });

    scored.sort((a, b) => b.score - a.score);
    const top3 = scored.slice(0, 3);

    // Save matches as PENDING
    const created = [];
    for (const ngo of top3) {
      // Avoid duplicate matches
      const existing = await prisma.nGOMatch.findFirst({
        where: { campaign_id: campaignId, ngo_id: ngo.id },
      });
      if (existing) {
        created.push(existing);
        continue;
      }
      const match = await prisma.nGOMatch.create({
        data: {
          campaign_id:  campaignId,
          ngo_id:       ngo.id,
          status:       'PENDING',
          match_score:  ngo.score,
        },
      });
      created.push(match);
    }

    res.json({
      success: true,
      message: `${created.length} NGO(s) matched. Admin must send emails manually.`,
      matches: created,
    });

  } catch (error) {
    console.error('NGO match error:', error);
    res.status(500).json({ success: false, error: 'NGO matching failed', detail: error.message });
  }
});

// ─────────────────────────────────────────
// 3. ADMIN SENDS EMAIL TO NGO
// POST /api/ngo/send-email/:match_id
// Auth: admin token
// ─────────────────────────────────────────
router.post('/send-email/:match_id', async (req, res) => {
  try {
    const admin = verifyAdmin(req, res);
    if (!admin) return;

    const matchId = parseInt(req.params.match_id);

    const match = await prisma.nGOMatch.findUnique({
      where: { id: matchId },
      include: {
        campaign: {
          include: { fund_needer: true },
        },
      },
    });

    if (!match) {
      return res.status(404).json({ success: false, error: 'Match not found' });
    }

    // Fetch NGO details from external ngo_db
    const ngoRows = await prisma.$queryRaw`
      SELECT ni.id, ni.name, ni.email
      FROM ngo_identity ni
      WHERE ni.id = ${match.ngo_id}
      LIMIT 1
    `;
    const ngo = ngoRows[0];
    if (!ngo || !ngo.email) {
      return res.status(400).json({ success: false, error: 'NGO email not found' });
    }

    // Generate response token (valid 7 days)
    const token   = crypto.randomBytes(32).toString('hex');
    const expires = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);

    await prisma.nGOMatch.update({
      where: { id: matchId },
      data: {
        response_token:      token,
        response_expires_at: expires,
        status:              'NOTIFIED',
        notified_at:         new Date(),
      },
    });

    const BASE_URL  = process.env.BACKEND_URL || 'http://localhost:3000';
    const acceptUrl = `${BASE_URL}/api/ngo/respond?token=${token}&status=ACCEPTED`;
    const rejectUrl = `${BASE_URL}/api/ngo/respond?token=${token}&status=REJECTED`;

    const html = buildEmailHTML(ngo, match.campaign, acceptUrl, rejectUrl);

    const transporter = getTransporter();
    await transporter.sendMail({
      from:    `"MediTrust" <${process.env.SMTP_USER}>`,
      to:      ngo.email,
      subject: `MediTrust — Support Request for "${match.campaign.title || 'Medical Campaign'}"`,
      html,
    });

    // Audit log
    await prisma.adminAuditLog.create({
      data: {
        admin_id:    admin.id || 1,
        action:      'NGO_EMAIL_SENT',
        target_type: 'ngo_match',
        target_id:   matchId,
        notes:       `Email sent to NGO ${ngo.name} (${ngo.email})`,
      },
    });

    res.json({ success: true, message: `Email sent to ${ngo.name} (${ngo.email})` });

  } catch (error) {
    console.error('Send email error:', error);
    res.status(500).json({ success: false, error: 'Failed to send email', detail: error.message });
  }
});

// ─────────────────────────────────────────
// 4. NGO RESPONDS VIA EMAIL LINK  ← GET so browser link works directly
// GET /api/ngo/respond?token=xxx&status=ACCEPTED
// Also supports POST for API calls (token + status in body)
// ─────────────────────────────────────────

async function handleNGORespond(token, status, res) {
  if (!token) {
    return res.status(400).json({ success: false, error: 'Response token is required' });
  }
  if (!['ACCEPTED', 'REJECTED'].includes(status)) {
    return res.status(400).json({ success: false, error: 'Status must be ACCEPTED or REJECTED' });
  }

  const match = await prisma.nGOMatch.findFirst({
    where: {
      response_token:      token,
      response_expires_at: { gt: new Date() },
    },
    include: { campaign: { include: { fund_needer: true } } },
  });

  if (!match) {
    return res.status(404).send(`
      <html><body style="font-family:Arial;text-align:center;padding:60px">
        <h2 style="color:#e74c3c">&#x26A0; Invalid or Expired Link</h2>
        <p>This response link has already been used or has expired.</p>
        <p>Please contact MediTrust if you need to update your response.</p>
      </body></html>
    `);
  }

  if (!['PENDING', 'NOTIFIED'].includes(match.status)) {
    return res.status(409).send(`
      <html><body style="font-family:Arial;text-align:center;padding:60px">
        <h2 style="color:#e67e22">Already Responded</h2>
        <p>You have already responded to this request (Status: ${match.status}).</p>
      </body></html>
    `);
  }

  await prisma.nGOMatch.update({
    where: { id: match.id },
    data: {
      status:              status,
      responded_at:        new Date(),
      response_token:      null,
      response_expires_at: null,
    },
  });

  await prisma.adminAuditLog.create({
    data: {
      admin_id:    1,
      action:      `NGO_RESPONDED_${status}`,
      target_type: 'ngo_match',
      target_id:   match.id,
      notes:       `NGO responded ${status} via email link`,
    },
  });

  const color   = status === 'ACCEPTED' ? '#27ae60' : '#e74c3c';
  const icon    = status === 'ACCEPTED' ? '✔' : '✘';
  const heading = status === 'ACCEPTED' ? 'Thank You for Accepting!' : 'Response Recorded';
  const body    = status === 'ACCEPTED'
    ? 'Thank you! Our team will contact you shortly to coordinate fund disbursement.'
    : 'We appreciate your response. We will explore other support options for this patient.';

  return res.send(`
    <html><body style="font-family:Arial;text-align:center;padding:60px;background:#f4f4f4">
      <div style="background:#fff;border-radius:10px;padding:40px;max-width:480px;margin:auto">
        <div style="font-size:56px">${icon}</div>
        <h2 style="color:${color}">${heading}</h2>
        <p style="color:#555">${body}</p>
        <p style="color:#aaa;font-size:12px">MediTrust Platform</p>
      </div>
    </body></html>
  `);
}

// GET — for email button links (browser opens directly)
router.get('/respond', async (req, res) => {
  try {
    const { token, status } = req.query;
    await handleNGORespond(token, status, res);
  } catch (error) {
    console.error('NGO respond (GET) error:', error);
    res.status(500).send('<h2>Something went wrong. Please try again.</h2>');
  }
});

// POST — for API/programmatic calls
router.post('/respond', async (req, res) => {
  try {
    const { token, status } = req.body;
    await handleNGORespond(token, status, res);
  } catch (error) {
    console.error('NGO respond (POST) error:', error);
    res.status(500).json({ success: false, error: 'Failed to record NGO response' });
  }
});

// ─────────────────────────────────────────
// 5. PATIENT — VIEW MATCHES FOR THEIR CAMPAIGN
// GET /api/ngo/campaign/:campaign_id
// Auth: patient token
// ─────────────────────────────────────────
router.get('/campaign/:campaign_id', async (req, res) => {
  try {
    const user = verifyPatient(req, res);
    if (!user) return;

    const campaignId = parseInt(req.params.campaign_id);

    const campaign = await prisma.campaign.findUnique({
      where: { id: campaignId },
    });

    if (!campaign) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    if (campaign.user_id !== user.id && user.role !== 'admin') {
      return res.status(403).json({ success: false, error: 'Access denied' });
    }

    const matches = await prisma.nGOMatch.findMany({
      where: { campaign_id: campaignId },
      orderBy: { match_score: 'desc' },
    });

    // Enrich with NGO details
    const enriched = [];
    for (const m of matches) {
      let ngoInfo = null;
      try {
        const rows = await prisma.$queryRaw`
          SELECT ni.id, ni.name, ni.email, ni.state, nfc.max_grant_amount
          FROM ngo_identity ni
          LEFT JOIN ngo_funding_capacity nfc ON nfc.ngo_id = ni.id
          WHERE ni.id = ${m.ngo_id}
          LIMIT 1
        `;
        ngoInfo = rows[0] || null;
      } catch (_) {}
      enriched.push({ ...m, ngo: ngoInfo });
    }

    res.json({
      success:    true,
      campaign_id: campaignId,
      total:      matches.length,
      matches:    enriched,
    });

  } catch (error) {
    console.error('Patient campaign matches error:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch campaign matches' });
  }
});

// ─────────────────────────────────────────
// 6. ADMIN — ALL MATCHES DASHBOARD
// GET /api/ngo/all-matches
// Auth: admin token
// ─────────────────────────────────────────
router.get('/all-matches', async (req, res) => {
  try {
    const admin = verifyAdmin(req, res);
    if (!admin) return;

    const matches = await prisma.nGOMatch.findMany({
      orderBy: { created_at: 'desc' },
      include: {
        campaign: {
          select: {
            id:          true,
            title:       true,
            disease:     true,
            goal_amount: true,
            state:       true,
            status:      true,
            fund_needer: {
              select: { full_name: true, email: true },
            },
          },
        },
      },
    });

    // Summary stats
    const summary = {
      total:    matches.length,
      pending:  matches.filter(m => m.status === 'PENDING').length,
      notified: matches.filter(m => m.status === 'NOTIFIED').length,
      accepted: matches.filter(m => m.status === 'ACCEPTED').length,
      rejected: matches.filter(m => m.status === 'REJECTED').length,
    };

    // Enrich with NGO names (best-effort)
    const enriched = [];
    for (const m of matches) {
      let ngoName = `NGO #${m.ngo_id}`;
      let ngoEmail = '';
      try {
        const rows = await prisma.$queryRaw`
          SELECT name, email FROM ngo_identity WHERE id = ${m.ngo_id} LIMIT 1
        `;
        if (rows[0]) {
          ngoName  = rows[0].name  || ngoName;
          ngoEmail = rows[0].email || '';
        }
      } catch (_) {}
      enriched.push({ ...m, ngo_name: ngoName, ngo_email: ngoEmail });
    }

    res.json({ success: true, summary, matches: enriched });

  } catch (error) {
    console.error('All matches error:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch matches', detail: error.message });
  }
});

// ─────────────────────────────────────────
// 7. ADMIN — MATCH DETAIL MODAL
// GET /api/ngo/match-detail/:match_id
// Auth: admin token
// ─────────────────────────────────────────
router.get('/match-detail/:match_id', async (req, res) => {
  try {
    const admin = verifyAdmin(req, res);
    if (!admin) return;

    const matchId = parseInt(req.params.match_id);

    const match = await prisma.nGOMatch.findUnique({
      where: { id: matchId },
      include: {
        campaign: {
          include: {
            fund_needer: true,
          },
        },
      },
    });

    if (!match) {
      return res.status(404).json({ success: false, error: 'Match not found' });
    }

    // Fetch full NGO details
    let ngoDetail = null;
    try {
      const rows = await prisma.$queryRaw`
        SELECT
          ni.id, ni.name, ni.email, ni.state, ni.phone,
          nmc.*,
          nfc.max_grant_amount, nfc.min_grant_amount,
          nsi.geographic_scope
        FROM ngo_identity ni
        LEFT JOIN ngo_medical_capability nmc ON nmc.ngo_id = ni.id
        LEFT JOIN ngo_funding_capacity   nfc ON nfc.ngo_id = ni.id
        LEFT JOIN ngo_system_info        nsi ON nsi.ngo_id = ni.id
        WHERE ni.id = ${match.ngo_id}
        LIMIT 1
      `;
      ngoDetail = rows[0] || null;
    } catch (_) {}

    res.json({ success: true, match, ngo: ngoDetail });

  } catch (error) {
    console.error('Match detail error:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch match detail' });
  }
});

// ─────────────────────────────────────────
// 8. ADMIN — SEARCH NGO DB
// GET /api/ngo/search?disease=cardiac&state=Kerala&age=adults
// Auth: admin token
// ─────────────────────────────────────────
router.get('/search', async (req, res) => {
  try {
    const admin = verifyAdmin(req, res);
    if (!admin) return;

    const { disease, state, age } = req.query;

    const validDiseases = ['cardiac', 'cancer', 'neuro', 'ortho', 'renal', 'liver', 'general'];
    const diseaseCol = validDiseases.includes(disease) ? disease : null;

    let whereClause = 'WHERE 1=1';
    if (state) {
      const safeState = state.replace(/'/g, "''");
      whereClause += ` AND (nsi.state = '${safeState}' OR nsi.geographic_scope = 'national')`;
    }
    if (diseaseCol) {
      whereClause += ` AND nmc.${diseaseCol} = true`;
    }

    const ngos = await prisma.$queryRawUnsafe(`
      SELECT
        ni.id, ni.name, ni.email, ni.state,
        nfc.max_grant_amount,
        nsi.geographic_scope
      FROM ngo_identity ni
      LEFT JOIN ngo_medical_capability nmc ON nmc.ngo_id = ni.id
      LEFT JOIN ngo_funding_capacity   nfc ON nfc.ngo_id = ni.id
      LEFT JOIN ngo_system_info        nsi ON nsi.ngo_id = ni.id
      ${whereClause}
      ORDER BY nfc.max_grant_amount DESC
      LIMIT 50
    `);

    res.json({ success: true, total: ngos.length, ngos });

  } catch (error) {
    console.error('NGO search error:', error);
    res.status(500).json({ success: false, error: 'Search failed', detail: error.message });
  }
});

// ─────────────────────────────────────────
// 9. NOTIFY NGOs OF HOSPITAL CHANGE
// POST /api/ngo/notify-hospital-change/:campaign_id
// Auth: patient token
// ─────────────────────────────────────────
router.post('/notify-hospital-change/:campaign_id', async (req, res) => {
  try {
    const user = verifyPatient(req, res);
    if (!user) return;

    const campaignId = parseInt(req.params.campaign_id);

    const campaign = await prisma.campaign.findUnique({
      where: { id: campaignId },
      include: { fund_needer: true },
    });

    if (!campaign) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    if (campaign.user_id !== user.id) {
      return res.status(403).json({ success: false, error: 'Access denied' });
    }

    // Get accepted/notified NGO matches
    const matches = await prisma.nGOMatch.findMany({
      where: {
        campaign_id: campaignId,
        status: { in: ['ACCEPTED', 'NOTIFIED'] },
      },
    });

    const transporter = getTransporter();
    let notified = 0;

    for (const m of matches) {
      try {
        const rows = await prisma.$queryRaw`
          SELECT name, email FROM ngo_identity WHERE id = ${m.ngo_id} LIMIT 1
        `;
        const ngo = rows[0];
        if (!ngo || !ngo.email) continue;

        await transporter.sendMail({
          from:    `"MediTrust" <${process.env.SMTP_USER}>`,
          to:      ngo.email,
          subject: `MediTrust — Hospital Update for Campaign "${campaign.title}"`,
          html: [
            '<div style="font-family:Arial;padding:20px">',
            '<h3>Hospital Change Notification</h3>',
            '<p>Dear ' + (ngo.name || 'NGO Partner') + ',</p>',
            '<p>The hospital associated with the campaign <strong>' + (campaign.title || '') + '</strong> has been updated.</p>',
            '<p>New Hospital: <strong>' + (req.body.new_hospital || 'Updated') + '</strong></p>',
            '<p>Please update your records accordingly.</p>',
            '<p>— MediTrust Team</p>',
            '</div>',
          ].join(''),
        });
        notified++;
      } catch (_) {}
    }

    res.json({ success: true, message: `${notified} NGO(s) notified of hospital change` });

  } catch (error) {
    console.error('Hospital change notify error:', error);
    res.status(500).json({ success: false, error: 'Notification failed' });
  }
});

module.exports = router;