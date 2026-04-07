const axios = require('axios');
const jwt = require('jsonwebtoken');

// Create admin token
const adminToken = jwt.sign(
  { id: 3, email: 'gajananberi@gmail.com', role: 'ADMIN' },
  '45e3b99e194a899848cc5a1444782842b8880a659a13cfaeb415d973572a6be05ca9e112d0d1ce9c624979b7606e38f5268d5051c7e1c7ab76871b684b6cac5b'
);

// Check current status after response attempt
axios.get('http://localhost:3000/api/ngo/all-matches', {
  headers: { 'Authorization': 'Bearer ' + adminToken }
}).then(response => {
  console.log('📊 Updated NGO Status:');
  response.data.matches.forEach((match, i) => {
    console.log(`${i+1}. ${match.ngo_name}: ${match.status}`);
  });
}).catch(error => {
  console.error('Error:', error.response?.data || error.message);
});
