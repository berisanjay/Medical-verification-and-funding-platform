const express = require('express');
const router = express.Router();
const prisma = require('../utils/prisma');
const { verifyAdmin } = require('../middleware/auth');

// ─────────────────────────────────────────
// GET SUGGESTIONS BY DISEASE
// ─────────────────────────────────────────
router.get('/:disease', async (req, res) => {
  try {
    const suggestions = await prisma.suggestion.findMany({
      where  : {
        disease               : { contains: req.params.disease },
        google_places_verified: true
      },
      orderBy: { created_at: 'desc' },
      take   : 10
    });

    res.json({ success: true, suggestions });

  } catch (error) {
    console.error('Get suggestions error:', error);
    res.status(500).json({ success: false, error: 'Failed to get suggestions' });
  }
});

// ─────────────────────────────────────────
// GET ALL SUGGESTIONS — Admin
// ─────────────────────────────────────────
router.get('/', verifyAdmin, async (req, res) => {
  try {
    const suggestions = await prisma.suggestion.findMany({
      orderBy: { created_at: 'desc' }
    });

    res.json({ success: true, suggestions });

  } catch (error) {
    console.error('Get all suggestions error:', error);
    res.status(500).json({ success: false, error: 'Failed to get suggestions' });
  }
});

module.exports = router;