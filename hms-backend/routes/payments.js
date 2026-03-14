const express = require('express');
const router = express.Router();
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

// Record payment — updates ledger automatically
router.post('/', async (req, res) => {
  try {
    const { patient_hms_id, amount, source, notes } = req.body;

    // Get current ledger
    const ledger = await prisma.ledger.findUnique({
      where: { patient_hms_id: parseInt(patient_hms_id) }
    });
    if (!ledger) return res.status(404).json({ success: false, error: 'Ledger not found' });

    const paymentAmount = parseFloat(amount);
    const newAmountPaid = parseFloat(ledger.amount_paid) + paymentAmount;
    const newOutstanding = parseFloat(ledger.outstanding_amount) - paymentAmount;

    // Record payment
    const payment = await prisma.payment.create({
      data: {
        patient_hms_id: parseInt(patient_hms_id),
        amount: paymentAmount,
        source: source || 'Crowdfunding',
        notes
      }
    });

    // Update ledger
    await prisma.ledger.update({
      where: { patient_hms_id: parseInt(patient_hms_id) },
      data: {
        amount_paid: newAmountPaid,
        outstanding_amount: newOutstanding < 0 ? 0 : newOutstanding
      }
    });

    res.json({
      success: true,
      payment,
      updated_ledger: {
        amount_paid: newAmountPaid,
        outstanding_amount: newOutstanding < 0 ? 0 : newOutstanding
      }
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get all payments for a patient
router.get('/:patient_hms_id', async (req, res) => {
  try {
    const payments = await prisma.payment.findMany({
      where: { patient_hms_id: parseInt(req.params.patient_hms_id) },
      orderBy: { paid_at: 'desc' }
    });
    res.json({ success: true, payments });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;