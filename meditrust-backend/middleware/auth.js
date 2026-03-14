const jwt = require('jsonwebtoken');

// Verify patient JWT
const verifyToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ success: false, error: 'Access token required' });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    return res.status(401).json({ success: false, error: 'Invalid or expired token' });
  }
};

// Verify admin JWT
const verifyAdmin = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ success: false, error: 'Admin token required' });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_ADMIN_SECRET);
    if (decoded.role !== 'ADMIN') {
      return res.status(403).json({ success: false, error: 'Admin access required' });
    }
    req.admin = decoded;
    next();
  } catch (error) {
    return res.status(403).json({ success: false, error: 'Invalid admin token' });
  }
};

// Verify internal Flask secret
const verifyFlaskSecret = (req, res, next) => {
  const secret = req.headers['x-flask-secret'];
  if (secret !== process.env.FLASK_INTERNAL_SECRET) {
    return res.status(403).json({ success: false, error: 'Unauthorized internal call' });
  }
  next();
};

module.exports = { verifyToken, verifyAdmin, verifyFlaskSecret };