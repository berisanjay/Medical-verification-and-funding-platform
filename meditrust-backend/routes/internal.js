const express = require('express');
const router = express.Router();
router.get('/', (req, res) => res.json({ message: 'Internal routes coming soon' }));
module.exports = router;