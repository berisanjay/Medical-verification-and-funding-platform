console.log('Testing auth middleware...');

try {
  const { verifyAdmin } = require('./middleware/auth');
  console.log('Auth middleware loaded successfully');
} catch (error) {
  console.error('Auth middleware error:', error);
}
