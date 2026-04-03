/**
 * MediTrust — NGO Matching System
 * Phase 11
 *
 * Flow:
 *   1. Campaign goes LIVE
 *   2. POST /api/ngo/match/:campaign_id  → find best NGOs from ngo_db
 *   3. Rank by disease match + age + state + funding capacity
 *   4. Send email to top 3 NGOs via Flask
 *   5. Track response — ACCEPTED / REJECTED
 *   6. Patient analytics shows NGO status
 *   7. On hospital change → notify all matched NGOs immediately
 */

const express  = require('express');
const router   = express.Router();
const axios    = require('axios');
const mysql    = require('mysql2/promise');
const prisma   = require('../utils/prisma');
const { verifyToken, verifyAdmin } = require('../middleware/auth');

// ─────────────────────────────────────────
// NGO DB CONNECTION — separate ngo_db database
// ─────────────────────────────────────────
let ngoPool = null;

const getNgoPool = () => {
  if (!ngoPool) {
    ngoPool = mysql.createPool({
      host    : process.env.NGO_DB_HOST     || 'localhost',
      user    : process.env.NGO_DB_USER     || 'root',
      password: process.env.NGO_DB_PASSWORD || '',
      database: process.env.NGO_DB_NAME     || 'ngo_db',
      waitForConnections: true,
      connectionLimit   : 10
    });
  }
  return ngoPool;
};

// ─────────────────────────────────────────
// HELPER — Map disease text to ngo_db column
// Mirrors Flask disease_mapper.py logic
// ─────────────────────────────────────────
const mapDiseaseToColumn = (diseaseText) => {
  if (!diseaseText) return 'disease_general';

  const text = diseaseText.toLowerCase();

  const categoryMap = {
    disease_cardiac    : ['coronary','cardiac','heart','cabg','bypass','angioplasty',
                          'myocardial','infarction','vessel','artery','stent','valve',
                          'pacemaker','angina','cardiomyopathy','arrhythmia','open heart',
                          'heart failure','atrial','ventricular','aorta'],
    disease_cancer     : ['cancer','tumor','tumour','carcinoma','lymphoma','leukemia',
                          'leukaemia','chemotherapy','oncology','malignant','sarcoma',
                          'melanoma','biopsy','metastasis','radiation','radiotherapy'],
    disease_neuro      : ['neuro','brain','stroke','paralysis','epilepsy','seizure',
                          'parkinson','alzheimer','dementia','spinal','spine','migraine',
                          'cerebral','nervous','multiple sclerosis','neuropathy','head injury'],
    disease_kidney     : ['kidney','renal','dialysis','nephro','urinary','bladder',
                          'nephrotic','nephritis','ckd','chronic kidney','kidney failure',
                          'kidney stone'],
    disease_liver      : ['liver','hepatic','hepatitis','cirrhosis','jaundice',
                          'gallbladder','bile','fatty liver','fibrosis','liver failure',
                          'liver transplant'],
    disease_orthopedic : ['bone','fracture','orthopedic','joint','knee','hip',
                          'replacement','disc','ligament','tendon','osteoporosis',
                          'arthritis','scoliosis','spinal cord','vertebra'],
    disease_eye        : ['eye','vision','retina','cataract','glaucoma','cornea',
                          'optic','blindness','ocular','vitreous','macular',
                          'diabetic retinopathy'],
    disease_rare       : ['rare','genetic','muscular dystrophy','thalassemia',
                          'hemophilia','down syndrome','wilson','gaucher','fabry',
                          'pompe','hunter syndrome','cystic fibrosis','sickle cell'],
  };

  for (const [column, keywords] of Object.entries(categoryMap)) {
    for (const keyword of keywords) {
      if (text.includes(keyword)) return column;
    }
  }

  return 'disease_general';
};

// ─────────────────────────────────────────
// HELPER — Map age to ngo_db age column
// ─────────────────────────────────────────
const mapAgeToColumn = (age) => {
  if (!age) return 'supports_adults';
  if (age < 18)  return 'supports_children';
  if (age >= 60) return 'supports_elderly';
  return 'supports_adults';
};

// ─────────────────────────────────────────
// HELPER — Notify Flask to send NGO email
// ─────────────────────────────────────────
const notifyFlask = async (path, data) => {
  try {
    await axios.post(`${process.env.FLASK_BASE_URL}${path}`, data, {
      headers: { 'x-flask-secret': process.env.FLASK_INTERNAL_SECRET },
      timeout: 10000
    });
  } catch (err) {
    console.log(`Flask notification failed ${path}:`, err.message);
  }
};

// ─────────────────────────────────────────
// MATCH NGOs — Core matching algorithm
// Called when campaign goes LIVE
// POST /api/ngo/match/:campaign_id
// ─────────────────────────────────────────
router.post('/match/:campaign_id', async (req, res) => {
  // Allow both patient token AND admin internal call
  const authHeader = req.headers['authorization'];
  const internalSecret = req.headers['x-flask-secret'];
  
  if (!authHeader && internalSecret !== process.env.FLASK_INTERNAL_SECRET) {
    return res.status(401).json({ success: false, error: 'Unauthorized' });
  }

  // Set req.user if token provided
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

    // 1. Get campaign details
    const campaign = await prisma.campaign.findUnique({
      where  : { id: campaignId },
      include: {
        patient : { select: { email: true, name: true } },
        hospital: true
      }
    });

    if (!campaign) {
      return res.status(404).json({ success: false, error: 'Campaign not found' });
    }

    // Skip ownership check for internal admin calls
    if (req.user && campaign.patient_id !== req.user.id) {
      return res.status(403).json({ success: false, error: 'Unauthorized' });
    }

    if (!['LIVE_CAMPAIGN', 'LIVE_UPDATED'].includes(campaign.status)) {
      return res.status(400).json({
        success: false,
        error  : 'NGO matching only available for live campaigns'
      });
    }

    // 2. Map disease and age to ngo_db columns
    const diseaseText   = req.body.disease || campaign.title;
    const patientAge    = campaign.patient_age;
    const patientState  = campaign.patient_state;
    const diseaseColumn = mapDiseaseToColumn(diseaseText);
    const ageColumn     = mapAgeToColumn(patientAge);

    console.log(`\n🔍 NGO Matching for Campaign ${campaignId}`);
    console.log(`   Disease Column : ${diseaseColumn}`);
    console.log(`   Age Column     : ${ageColumn}`);
    console.log(`   Patient State  : ${patientState}`);

    // 3. Query ngo_db — join all 4 tables
    const pool = getNgoPool();

    const [ngos] = await pool.execute(`
      SELECT
        i.ngo_id,
        i.ngo_name,
        i.contact_email,
        i.phone_number,
        i.alternate_phone,
        i.headquarters_city,
        i.state,
        i.website_url,
        i.registration_number,
        m.${diseaseColumn}        AS disease_match,
        m.${ageColumn}            AS age_match,
        m.disease_general,
        f.max_grant_per_patient_inr,
        f.avg_grant_per_patient_inr,
        f.annual_budget_range,
        f.csr_connected,
        f.government_support,
        f.registration_80G,
        e.income_eligibility_max_inr,
        e.online_application_available,
        e.processing_time_days,
        s.geographic_scope,
        s.primary_state,
        s.hospital_partnership_known
      FROM ngo_identity i
      JOIN ngo_medical_capability m  ON i.ngo_id = m.ngo_id
      JOIN ngo_funding_capacity   f  ON i.ngo_id = f.ngo_id
      JOIN ngo_eligibility_application e ON i.ngo_id = e.ngo_id
      JOIN ngo_system_info        s  ON i.ngo_id = s.ngo_id
      WHERE
        i.contact_email IS NOT NULL
        AND (m.${diseaseColumn} = 1 OR m.disease_general = 1)
        AND m.${ageColumn} = 1
    `);

    if (ngos.length === 0) {
      return res.json({
        success: true,
        message: 'No matching NGOs found for this case',
        matched : 0,
        ngos   : []
      });
    }

    // 4. Rank NGOs by score
    const ranked = ngos.map(ngo => {
      let score = 0;

      // Disease match (exact vs general)
      if (ngo.disease_match) score += 40;
      else if (ngo.disease_general) score += 10;

      // State match
      if (ngo.primary_state &&
          patientState &&
          ngo.primary_state.toLowerCase().includes(patientState.toLowerCase())) {
        score += 25;
      }

      // Geographic scope — national is better than regional
      if (ngo.geographic_scope === 'National') score += 15;
      else if (ngo.geographic_scope === 'State')    score += 10;
      else if (ngo.geographic_scope === 'Regional') score += 5;

      // Funding capacity
      const maxGrant = parseFloat(ngo.max_grant_per_patient_inr || 0);
      const needed   = parseFloat(campaign.verified_amount || 0);
      if (maxGrant >= needed) score += 20;
      else if (maxGrant > 0)  score += 10;

      // Hospital partnership bonus
      if (ngo.hospital_partnership_known === 'Yes') score += 10;

      // Online application bonus
      if (ngo.online_application_available) score += 5;

      // CSR / Government support bonus
      if (ngo.csr_connected)     score += 5;
      if (ngo.government_support) score += 5;

      return { ...ngo, match_score: score };
    });

    // Sort by score descending, take top 3
    const top3 = ranked
      .sort((a, b) => b.match_score - a.match_score)
      .slice(0, 3);

    console.log(`   Found ${ngos.length} matching NGOs, top ${top3.length} selected`);
    top3.forEach(n => console.log(`   → ${n.ngo_name} (score: ${n.match_score})`));

    // 5. Save NGO matches to meditrust DB + send emails
    const savedMatches = [];

    for (const ngo of top3) {
      // Check if already notified
      const existing = await prisma.nGOMatch.findFirst({
        where: {
          campaign_id: campaignId,
          ngo_id     : ngo.ngo_id
        }
      });

      if (!existing) {
        // Save to NGOMatch table
        const match = await prisma.nGOMatch.create({
          data: {
            campaign_id: campaignId,
            ngo_id     : ngo.ngo_id,
            status     : 'NOTIFIED'
          }
        });

        // Send email via Flask
        await notifyFlask('/notify/ngo-match', {
          to_email      : ngo.contact_email,
          ngo_name      : ngo.ngo_name,
          campaign_title: campaign.title,
          patient_name  : campaign.patient_full_name,
          disease       : diseaseText,
          hospital_name : campaign.hospital?.name || 'Verified Hospital',
          hospital_city : campaign.hospital?.city || campaign.patient_city,
          documents_url : campaign.public_url || `meditrust.in/campaign/${campaignId}`
        });

        savedMatches.push({
          match_id  : match.id, // Use the created match object's ID
          ngo_id    : ngo.ngo_id,
          ngo_name  : ngo.ngo_name,
          email     : ngo.contact_email,
          city      : ngo.headquarters_city,
          state     : ngo.state,
          score     : ngo.match_score,
          max_grant : ngo.max_grant_per_patient_inr
        });

        console.log(`   ✅ Notified: ${ngo.ngo_name} <${ngo.contact_email}>`);
      } else {
        console.log(`   ⚠️  Already notified: ${ngo.ngo_name}`);
      }
    }

    // 6. Log admin audit
    await prisma.adminAuditLog.create({
      data: {
        admin_id    : req.user.id,
        action      : 'NGO_MATCHED',
        target_type : 'campaign',
        target_id   : campaignId,
        notes       : `Matched and notified ${savedMatches.length} NGOs for campaign ${campaignId}`
      }
    }).catch(() => {}); // Non-critical

    res.json({
      success : true,
      message : `${savedMatches.length} NGOs matched and notified successfully`,
      matched : savedMatches.length,
      disease_matched: diseaseColumn,
      ngos    : savedMatches
    });

  } catch (error) {
    console.error('NGO match error:', error);
    res.status(500).json({ success: false, error: 'NGO matching failed: ' + error.message });
  }
});

// ─────────────────────────────────────────
// NGO RESPONDS — Accept or Reject case
// PUT /api/ngo/respond/:match_id
// Called when NGO clicks accept/reject in email link
// ─────────────────────────────────────────
router.put('/respond/:match_id', async (req, res) => {
  try {
    const matchId  = parseInt(req.params.match_id);
    const { status, notes } = req.body; // ACCEPTED or REJECTED

    if (!['ACCEPTED', 'REJECTED'].includes(status)) {
      return res.status(400).json({
        success: false,
        error  : 'Status must be ACCEPTED or REJECTED'
      });
    }

    const match = await prisma.nGOMatch.findUnique({
      where  : { id: matchId },
      include: { campaign: true }
    });

    if (!match) {
      return res.status(404).json({ success: false, error: 'Match not found' });
    }

    await prisma.nGOMatch.update({
      where: { id: matchId },
      data : {
        status      : status,
        responded_at: new Date()
      }
    });

    res.json({
      success: true,
      message: `NGO response recorded: ${status}`,
      match_id: matchId
    });

  } catch (error) {
    console.error('NGO respond error:', error);
    res.status(500).json({ success: false, error: 'Failed to record NGO response' });
  }
});

// ─────────────────────────────────────────
// GET NGO MATCHES FOR CAMPAIGN — Patient dashboard
// GET /api/ngo/campaign/:campaign_id
// ─────────────────────────────────────────
router.get('/campaign/:campaign_id', verifyToken, async (req, res) => {
  try {
    const campaignId = parseInt(req.params.campaign_id);

    const campaign = await prisma.campaign.findUnique({
      where: { id: campaignId }
    });

    if (!campaign || campaign.patient_id !== req.user.id) {
      return res.status(403).json({ success: false, error: 'Unauthorized' });
    }

    const matches = await prisma.nGOMatch.findMany({
      where  : { campaign_id: campaignId },
      include: { ngo: { select: { name: true, email: true, city: true, state: true } } },
      orderBy: { notified_at: 'desc' }
    });

    // Also fetch NGO details from ngo_db for richer info
    const pool = getNgoPool();
    const enriched = await Promise.all(matches.map(async (match) => {
      try {
        const [rows] = await pool.execute(
          `SELECT i.ngo_name, i.headquarters_city, i.state, i.website_url,
                  i.phone_number, f.max_grant_per_patient_inr
           FROM ngo_identity i
           JOIN ngo_funding_capacity f ON i.ngo_id = f.ngo_id
           WHERE i.ngo_id = ?`,
          [match.ngo_id]
        );
        return {
          match_id    : match.id,
          ngo_id      : match.ngo_id,
          ngo_name    : rows[0]?.ngo_name || 'Unknown NGO',
          city        : rows[0]?.headquarters_city,
          state       : rows[0]?.state,
          website     : rows[0]?.website_url,
          phone       : rows[0]?.phone_number,
          max_grant   : rows[0]?.max_grant_per_patient_inr,
          status      : match.status,
          notified_at : match.notified_at,
          responded_at: match.responded_at
        };
      } catch {
        return {
          match_id    : match.id,
          ngo_id      : match.ngo_id,
          ngo_name    : 'NGO',
          status      : match.status,
          notified_at : match.notified_at,
          responded_at: match.responded_at
        };
      }
    }));

    const summary = {
      total_notified : matches.length,
      accepted       : matches.filter(m => m.status === 'ACCEPTED').length,
      rejected       : matches.filter(m => m.status === 'REJECTED').length,
      pending        : matches.filter(m => m.status === 'NOTIFIED' || m.status === 'PENDING').length
    };

    res.json({ success: true, summary, matches: enriched });

  } catch (error) {
    console.error('Get NGO matches error:', error);
    res.status(500).json({ success: false, error: 'Failed to get NGO matches' });
  }
});

// ─────────────────────────────────────────
// NOTIFY NGOs ON HOSPITAL CHANGE
// POST /api/ngo/notify-hospital-change/:campaign_id
// Called automatically when hospital changes
// ─────────────────────────────────────────
router.post('/notify-hospital-change/:campaign_id', verifyToken, async (req, res) => {
  try {
    const campaignId              = parseInt(req.params.campaign_id);
    const { old_hospital, new_hospital } = req.body;

    const campaign = await prisma.campaign.findUnique({
      where: { id: campaignId }
    });

    if (!campaign || campaign.patient_id !== req.user.id) {
      return res.status(403).json({ success: false, error: 'Unauthorized' });
    }

    // Get all matched NGOs for this campaign
    const matches = await prisma.nGOMatch.findMany({
      where: { campaign_id: campaignId }
    });

    if (matches.length === 0) {
      return res.json({
        success: true,
        message: 'No NGOs to notify',
        notified: 0
      });
    }

    const pool = getNgoPool();
    let notifiedCount = 0;

    for (const match of matches) {
      try {
        const [rows] = await pool.execute(
          'SELECT ngo_name, contact_email FROM ngo_identity WHERE ngo_id = ?',
          [match.ngo_id]
        );

        if (rows[0]?.contact_email) {
          await notifyFlask('/notify/hospital-change', {
            to_email    : rows[0].contact_email,
            ngo_name    : rows[0].ngo_name,
            campaign_title: campaign.title,
            patient_name: campaign.patient_full_name,
            old_hospital: old_hospital || 'Previous Hospital',
            new_hospital: new_hospital || 'New Hospital'
          });
          notifiedCount++;
        }
      } catch (err) {
        console.log(`Failed to notify NGO ${match.ngo_id}:`, err.message);
      }
    }

    res.json({
      success : true,
      message : `${notifiedCount} NGOs notified of hospital change`,
      notified: notifiedCount
    });

  } catch (error) {
    console.error('NGO hospital change notify error:', error);
    res.status(500).json({ success: false, error: 'Failed to notify NGOs' });
  }
});

// ─────────────────────────────────────────
// SEARCH NGOs IN ngo_db — Admin only
// GET /api/ngo/search?disease=cardiac&state=Telangana
// ─────────────────────────────────────────
router.get('/search', verifyAdmin, async (req, res) => {
  try {
    const { disease, state, age } = req.query;

    const diseaseColumn = disease ? mapDiseaseToColumn(disease) : 'disease_general';
    const ageColumn     = age     ? mapAgeToColumn(parseInt(age)) : 'supports_adults';

    const pool = getNgoPool();

    let query = `
      SELECT
        i.ngo_id, i.ngo_name, i.contact_email, i.phone_number,
        i.headquarters_city, i.state, i.website_url,
        f.max_grant_per_patient_inr, f.annual_budget_range,
        s.geographic_scope, s.primary_state,
        s.hospital_partnership_known,
        e.online_application_available, e.processing_time_days
      FROM ngo_identity i
      JOIN ngo_medical_capability m ON i.ngo_id = m.ngo_id
      JOIN ngo_funding_capacity f   ON i.ngo_id = f.ngo_id
      JOIN ngo_system_info s        ON i.ngo_id = s.ngo_id
      JOIN ngo_eligibility_application e ON i.ngo_id = e.ngo_id
      WHERE (m.${diseaseColumn} = 1 OR m.disease_general = 1)
        AND m.${ageColumn} = 1
    `;

    const params = [];
    if (state) {
      query += ` AND (s.primary_state LIKE ? OR s.geographic_scope = 'National')`;
      params.push(`%${state}%`);
    }

    query += ` ORDER BY f.max_grant_per_patient_inr DESC LIMIT 20`;

    const [ngos] = await pool.execute(query, params);

    res.json({ success: true, count: ngos.length, ngos });

  } catch (error) {
    console.error('NGO search error:', error);
    res.status(500).json({ success: false, error: 'NGO search failed: ' + error.message });
  }
});

// ─────────────────────────────────────────
// GET ALL NGO MATCHES — Admin dashboard
// GET /api/ngo/all-matches
// ─────────────────────────────────────────
router.get('/all-matches', verifyAdmin, async (req, res) => {
  try {
    const matches = await prisma.nGOMatch.findMany({
      include: {
        campaign: {
          select: {
            id              : true,
            title           : true,
            patient_full_name: true,
            status          : true
          }
        },
        ngo: {
          select: {
            name: true,
            email: true,
            city: true,
            state: true
          }
        }
      },
      orderBy: { notified_at: 'desc' },
      take   : 100
    });

    // Also fetch NGO details from ngo_db for richer info
    const pool = getNgoPool();
    const enriched = await Promise.all(matches.map(async (match) => {
      try {
        const [rows] = await pool.execute(
          `SELECT i.ngo_name, i.headquarters_city, i.state, i.website_url,
                  i.phone_number, f.max_grant_per_patient_inr
           FROM ngo_identity i
           JOIN ngo_funding_capacity f ON i.ngo_id = f.ngo_id
           WHERE i.ngo_id = ?`,
          [match.ngo_id]
        );
        return {
          ...match,
          ngo_name: rows[0]?.ngo_name || 'Unknown NGO',
          ngo_email: rows[0]?.contact_email || 'unknown@example.com',
          city: rows[0]?.headquarters_city || 'Unknown City',
          state: rows[0]?.state || 'Unknown State',
          website: rows[0]?.website_url || '#',
          phone: rows[0]?.phone_number || 'Unknown Phone',
          max_grant: rows[0]?.max_grant_per_patient_inr || 0
        };
      } catch {
        return {
          ...match,
          ngo_name: 'NGO',
          ngo_email: 'unknown@example.com',
          city: 'Unknown City',
          state: 'Unknown State',
          website: '#',
          phone: 'Unknown Phone',
          max_grant: 0
        };
      }
    }));

    const summary = {
      total   : matches.length,
      accepted: matches.filter(m => m.status === 'ACCEPTED').length,
      rejected: matches.filter(m => m.status === 'REJECTED').length,
      pending : matches.filter(m => ['NOTIFIED', 'PENDING'].includes(m.status)).length
    };

  } catch (error) {
    console.error('Get NGO match error:', error);
    res.status(500).json({ success: false, error: 'Failed to get NGO match' });
  }
});

module.exports = router;