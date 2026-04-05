const axios = require('axios');
const jwt = require('jsonwebtoken');

// Create admin token with correct secret
const adminToken = jwt.sign(
  { id: 3, email: 'gajananberi@gmail.com', role: 'ADMIN' },
  '45e3b99e194a899848cc5a1444782842b8880a659a13cfaeb415d973572a6be05ca9e112d0d1ce9c624979b7606e38f5268d5051c7e1c7ab76871b684b6cac5b'
);

axios.get('http://localhost:3000/api/ngo/all-matches', {
  headers: { 'Authorization': 'Bearer ' + adminToken }
}).then(response => {
  console.log('SUCCESS! NGO matches:', response.data.summary);
  console.log('Matches found:', response.data.matches.length);
  response.data.matches.forEach(m => {
    console.log(`- ${m.ngo_name}: ${m.status}`);
  });
}).catch(error => {
  console.error('Error:', error.response?.data || error.message);
});
