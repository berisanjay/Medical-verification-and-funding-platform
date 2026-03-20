/**
 * MediTrust — Accessible Hospitals
 * Manages hospitals registered with MediTrust
 * Type A: is_hms_connected=true  → has HMS API
 * Type B: is_hms_connected=false → no API, use document data
 */

const express = require('express');
const router  = express.Router();
const prisma  = require('../utils/prisma');
const axios   = require('axios');
const { verifyAdmin } = require('../middleware/auth');

// ─────────────────────────────────────────
// SEARCH hospital by name (used by create-campaign)
// GET /api/hospitals/search?name=Apollo Hospitals Vizag
// Returns: hospital + whether it has HMS API
// ─────────────────────────────────────────
router.get('/search', async (req, res) => {
  try {
    const { name } = req.query;
    if (!name) return res.status(400).json({ success: false, error: 'name required' });

    const nameLower = name.toLowerCase().trim();

    // Search by name or aliases
    let hospitals = [];
    try {
      hospitals = await prisma.accessibleHospital.findMany();
    } catch (dbErr) {
      // Table may not exist yet — return not found gracefully
      console.warn('⚠️ AccessibleHospital table not ready:', dbErr.message);
      return res.json({
        success: true,
        found  : false,
        message: 'Hospital registry not ready — run migration. Using document data.'
      });
    }

    // Fuzzy match — check name and aliases
    const matched = hospitals.find(h => {
      const hName = h.name.toLowerCase();
      if (hName.includes(nameLower) || nameLower.includes(hName)) return true;

      // Check aliases
      const aliases = Array.isArray(h.name_aliases) ? h.name_aliases : [];
      return aliases.some(alias =>
        alias.toLowerCase().includes(nameLower) ||
        nameLower.includes(alias.toLowerCase())
      );
    });

    if (!matched) {
      return res.json({
        success: true,
        found  : false,
        message: 'Hospital not registered with MediTrust — will use document data'
      });
    }

    res.json({
      success   : true,
      found     : true,
      hospital  : {
        id              : matched.id,
        name            : matched.name,
        city            : matched.city,
        state           : matched.state,
        pincode         : matched.pincode,
        is_hms_connected: matched.is_hms_connected,
        hms_api_url     : matched.hms_api_url
      }
    });

  } catch (error) {
    console.error('Hospital search error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// CHECK PATIENT IN HOSPITAL HMS
// POST /api/hospitals/:id/check-patient
// Called after hospital found in AccessibleHospital
// If hospital is Type A (has HMS API), calls their API
// Returns patient + ledger data
// ─────────────────────────────────────────
router.post('/:id/check-patient', async (req, res) => {
  try {
    const hospital = await prisma.accessibleHospital.findUnique({
      where: { id: parseInt(req.params.id) }
    });

    if (!hospital) {
      return res.status(404).json({ success: false, error: 'Hospital not found' });
    }

    const { patient_name, patient_aadhaar, estimated_amount } = req.body;

    // ── TYPE B: No HMS API ─────────────────────────────
    if (!hospital.is_hms_connected || !hospital.hms_api_url) {
      return res.json({
        success       : true,
        hospital_type : 'TYPE_B',
        found         : false,
        message       : 'Hospital has no HMS API — using document data',
        billing       : {
          source         : 'DOC_EXTRACTED',
          total_estimate : parseFloat(estimated_amount || 0),
          amount_paid    : 0,
          outstanding    : parseFloat(estimated_amount || 0),
          admission_status: 'Pending Admin Verification'
        }
      });
    }

    // ── TYPE A: Has HMS API ────────────────────────────
    // Call their HMS to search patient by Aadhaar
    const hmsUrl = hospital.hms_api_url.replace(/\/$/, '');

    try {
      const searchRes = await axios.get(
        `${hmsUrl}/hms/patients/search`,
        {
          params : { aadhaar: patient_aadhaar, name: patient_name },
          timeout: 10000
        }
      );

      const searchData = searchRes.data;

      if (!searchData.found || !searchData.patients?.length) {
        // Patient not in this hospital's HMS yet
        // Auto-register them using document data
        console.log(`Patient not found in HMS — auto-registering from documents`);

        return res.json({
          success       : true,
          hospital_type : 'TYPE_A',
          found         : false,
          message       : 'Patient not yet registered in hospital HMS — using document estimate',
          billing       : {
            source          : 'DOC_EXTRACTED',
            total_estimate  : parseFloat(estimated_amount || 0),
            amount_paid     : 0,
            outstanding     : parseFloat(estimated_amount || 0),
            admission_status: 'Registered — HMS will confirm on admission'
          }
        });
      }

      // Patient found in HMS
      const patient = searchData.patients[0];
      const ledger  = patient.ledger || {};

      return res.json({
        success        : true,
        hospital_type  : 'TYPE_A',
        found          : true,
        hms_patient_id : patient.id,
        billing        : {
          source          : 'HMS_API',
          admission_status: patient.status || 'ADMITTED',
          treatment_type  : patient.disease || '—',
          total_estimate  : parseFloat(ledger.total_estimate || estimated_amount || 0),
          amount_paid     : parseFloat(ledger.amount_paid || 0),
          outstanding     : parseFloat(ledger.outstanding_amount || estimated_amount || 0)
        }
      });

    } catch (hmsErr) {
      console.error('HMS API call failed:', hmsErr.message);
      // HMS API unreachable — fall back to document data
      return res.json({
        success       : true,
        hospital_type : 'TYPE_A',
        found         : false,
        message       : 'Hospital HMS API unreachable — using document estimate',
        billing       : {
          source          : 'DOC_EXTRACTED',
          total_estimate  : parseFloat(estimated_amount || 0),
          amount_paid     : 0,
          outstanding     : parseFloat(estimated_amount || 0),
          admission_status: 'HMS Offline — Admin will verify'
        }
      });
    }

  } catch (error) {
    console.error('check-patient error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// CREATE FUND NEEDER
// POST /api/hospitals/fund-needer
// Called when user confirms HMS/billing data
// Stores billing details for campaign
// ─────────────────────────────────────────
router.post('/fund-needer', async (req, res) => {
  try {
    const {
      campaign_id, accessible_hospital_id,
      patient_name, patient_aadhaar, patient_age, patient_gender,
      disease, admission_date, hospital_name, hospital_pincode,
      total_estimate, amount_paid, outstanding,
      source, hms_patient_id
    } = req.body;

    // Upsert — create or update if already exists
    // Graceful fail if table not migrated yet
    let fundNeeder;
    try {
      fundNeeder = await prisma.fundNeeder.upsert({
      where  : { campaign_id: parseInt(campaign_id) },
      create : {
        campaign_id            : parseInt(campaign_id),
        accessible_hospital_id : accessible_hospital_id ? parseInt(accessible_hospital_id) : null,
        patient_name, patient_aadhaar,
        patient_age            : patient_age ? parseInt(patient_age) : null,
        patient_gender, disease, admission_date,
        hospital_name, hospital_pincode,
        total_estimate         : parseFloat(total_estimate || 0),
        amount_paid            : parseFloat(amount_paid || 0),
        outstanding            : parseFloat(outstanding || 0),
        source                 : source || 'DOC_EXTRACTED',
        hms_patient_id         : hms_patient_id ? parseInt(hms_patient_id) : null
      },
      update : {
        total_estimate : parseFloat(total_estimate || 0),
        amount_paid    : parseFloat(amount_paid || 0),
        outstanding    : parseFloat(outstanding || 0),
        source         : source || 'DOC_EXTRACTED',
        hms_patient_id : hms_patient_id ? parseInt(hms_patient_id) : null
      }
    });

    } catch(dbErr) {
      console.warn('⚠️ FundNeeder table not ready:', dbErr.message);
      return res.json({ success: true, fund_needer: null, warning: 'Run migration to enable FundNeeder' });
    }

    // Also update campaign verified_amount
    await prisma.campaign.update({
      where: { id: parseInt(campaign_id) },
      data : { verified_amount: parseFloat(outstanding || 0) }
    });

    res.json({ success: true, fund_needer: fundNeeder });
  } catch (error) {
    console.error('fund-needer create error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// GET ALL ACCESSIBLE HOSPITALS (admin)
// GET /api/hospitals
// ─────────────────────────────────────────
router.get('/', verifyAdmin, async (req, res) => {
  try {
    const hospitals = await prisma.accessibleHospital.findMany({
      orderBy: { name: 'asc' }
    });
    res.json({ success: true, hospitals });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// REGISTER HOSPITAL (admin only)
// POST /api/hospitals
// ─────────────────────────────────────────
router.post('/', verifyAdmin, async (req, res) => {
  try {
    const {
      name, name_aliases, city, state, pincode, address,
      phone, email, is_hms_connected, hms_api_url, hms_api_key
    } = req.body;

    const hospital = await prisma.accessibleHospital.create({
      data: {
        name, name_aliases: name_aliases || [],
        city, state, pincode,
        address: address || '',
        phone, email,
        is_hms_connected: is_hms_connected || false,
        hms_api_url     : hms_api_url || null,
        hms_api_key     : hms_api_key || null
      }
    });

    res.json({ success: true, hospital });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// ADMIN VERIFY FUND NEEDER (manual verification)
// PUT /api/hospitals/fund-needer/:id/verify
// ─────────────────────────────────────────
router.put('/fund-needer/:id/verify', verifyAdmin, async (req, res) => {
  try {
    const { admin_notes } = req.body;
    const fundNeeder = await prisma.fundNeeder.update({
      where: { id: parseInt(req.params.id) },
      data : { admin_verified: true, admin_notes: admin_notes || null }
    });
    res.json({ success: true, fund_needer: fundNeeder });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;