const express = require('express');
const router = express.Router();
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

// Create hospital
router.post('/', async (req, res) => {
  try {
    const { name, city, state, pincode, address, phone, email } = req.body;
    const hospital = await prisma.hospital.create({
      data: { name, city, state, pincode, address, phone, email }
    });
    res.json({ success: true, hospital });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get all hospitals
router.get('/', async (req, res) => {
  try {
    const hospitals = await prisma.hospital.findMany();
    res.json({ success: true, hospitals });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get hospital by id
router.get('/:id', async (req, res) => {
  try {
    const hospital = await prisma.hospital.findUnique({
      where: { id: parseInt(req.params.id) }
    });
    if (!hospital) return res.status(404).json({ success: false, error: 'Hospital not found' });
    res.json({ success: true, hospital });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;