const express = require('express');
const router  = express.Router();
const { PrismaClient } = require('@prisma/client');
const prisma  = new PrismaClient();

// ─────────────────────────────────────────
// CREATE patient + ledger
// ─────────────────────────────────────────
router.post('/', async (req, res) => {
  try {
    const {
      patient_name, age, gender, aadhaar_number,
      disease, admission_date, hospital_id, total_estimate
    } = req.body;

    const patient = await prisma.patient.create({
      data: {
        patient_name, age, gender, aadhaar_number,
        disease,
        admission_date : admission_date ? new Date(admission_date) : null,
        hospital_id    : parseInt(hospital_id),
        ledger: {
          create: {
            total_estimate    : parseFloat(total_estimate),
            outstanding_amount: parseFloat(total_estimate),
            amount_paid       : 0
          }
        }
      },
      include: { ledger: true }
    });

    res.json({ success: true, patient_hms_id: patient.id, patient });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// SEARCH patients — by Aadhaar or name
// Called by MediTrust admin during verification
// MUST be before /:id routes
// ─────────────────────────────────────────
router.get('/search', async (req, res) => {
  try {
    const { aadhaar, name } = req.query;

    if (!aadhaar && !name) {
      return res.status(400).json({
        success: false,
        error  : 'Provide aadhaar or name to search'
      });
    }

    const where = {};

    if (aadhaar) {
      // Remove spaces and dashes before comparing
      const clean = aadhaar.replace(/[\s\-]/g, '');
      where.aadhaar_number = { contains: clean };
    }

    if (name) {
      where.patient_name = { contains: name, mode: 'insensitive' };
    }

    const patients = await prisma.patient.findMany({
      where,
      include: {
        hospital: true,
        ledger  : true,
        payments: { orderBy: { paid_at: 'desc' }, take: 5 }
      },
      take: 5
    });

    res.json({
      success : true,
      found   : patients.length > 0,
      count   : patients.length,
      patients
    });

  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// SEARCH by Aadhaar — exact match
// Called by MediTrust admin review route
// MUST be before /:id route
// ─────────────────────────────────────────
router.get('/aadhaar/:aadhaar', async (req, res) => {
  try {
    const cleanAadhaar = req.params.aadhaar.replace(/[\s\-]/g, '');

    const patient = await prisma.patient.findFirst({
      where  : { aadhaar_number: { contains: cleanAadhaar } },
      include: { hospital: true, ledger: true, payments: true }
    });

    if (!patient) {
      return res.json({
        success: true,
        found  : false,
        patient: null,
        message: 'Patient not found in HMS'
      });
    }

    res.json({
      success: true,
      found  : true,
      patient
    });

  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// GET outstanding amount
// CRITICAL — called before every payout
// ─────────────────────────────────────────
router.get('/:id/outstanding', async (req, res) => {
  try {
    const ledger = await prisma.ledger.findUnique({
      where: { patient_hms_id: parseInt(req.params.id) }
    });
    if (!ledger) return res.status(404).json({ success: false, error: 'Ledger not found' });
    res.json({
      success    : true,
      outstanding: ledger.outstanding_amount,
      estimate   : ledger.total_estimate,
      paid       : ledger.amount_paid
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// GET patient status
// ─────────────────────────────────────────
router.get('/:id/status', async (req, res) => {
  try {
    const patient = await prisma.patient.findUnique({
      where  : { id: parseInt(req.params.id) },
      include: { hospital: true, ledger: true }
    });
    if (!patient) return res.status(404).json({ success: false, error: 'Patient not found' });
    res.json({ success: true, status: patient.status, patient });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// DISCHARGE patient — stops all payouts
// ─────────────────────────────────────────
router.put('/:id/discharge', async (req, res) => {
  try {
    const patient = await prisma.patient.update({
      where: { id: parseInt(req.params.id) },
      data : { status: 'DISCHARGED' }
    });
    res.json({ success: true, message: 'Patient discharged, payouts stopped', patient });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// UPDATE hospital — locks new estimate
// ─────────────────────────────────────────
router.put('/:id/hospital', async (req, res) => {
  try {
    const { hospital_id, new_estimate } = req.body;
    const patient = await prisma.patient.update({
      where: { id: parseInt(req.params.id) },
      data : { hospital_id: parseInt(hospital_id) }
    });
    const ledger = await prisma.ledger.update({
      where: { patient_hms_id: parseInt(req.params.id) },
      data : {
        total_estimate    : parseFloat(new_estimate),
        outstanding_amount: parseFloat(new_estimate)
      }
    });
    res.json({ success: true, message: 'Hospital updated, new estimate locked', patient, ledger });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ─────────────────────────────────────────
// GET full patient details by ID
// MUST be LAST — catches /:id
// ─────────────────────────────────────────
router.get('/:id', async (req, res) => {
  try {
    const patient = await prisma.patient.findUnique({
      where  : { id: parseInt(req.params.id) },
      include: { hospital: true, ledger: true, payments: true }
    });
    if (!patient) return res.status(404).json({ success: false, error: 'Patient not found' });
    res.json({ success: true, patient });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;