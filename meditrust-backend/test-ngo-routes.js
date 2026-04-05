console.log('Testing NGO routes...');

try {
  const ngoRoutes = require('./routes/ngo');
  console.log('NGO routes loaded successfully');
  console.log('Available methods:', Object.getOwnPropertyNames(ngoRoutes));
} catch (error) {
  console.error('Error loading NGO routes:', error.message);
}
