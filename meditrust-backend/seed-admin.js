const axios = require('axios');

axios.post('http://localhost:3000/api/admin/seed', {
  secret: 'MediTrustAdmin@2026SecretKey'
}, {
  headers: { 'Content-Type': 'application/json' }
}).then(response => {
  console.log('Seed response:', response.data);
}).catch(error => {
  console.error('Seed error:', error.response?.data || error.message);
});
