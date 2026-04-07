const axios = require('axios');
const jwt = require('jsonwebtoken');

console.log('Debugging Fund Release...\n');

// Create admin token
const adminToken = jwt.sign(
  { id: 3, email: 'gajananberi@gmail.com', role: 'ADMIN' },
  '45e3b99e194a899848cc5a1444782842b8880a659a13cfaeb415d973572a6be05ca9e112d0d1ce9c624979b7606e38f5268d5051c7e1c7ab76871b684b6cac5b'
);

console.log('Admin Token created successfully');

// Test fund release step by step
const releaseData = {
  campaign_id: 1,
  amount: 25000
};

console.log('Sending fund release request:', releaseData);

axios.post('http://localhost:3000/api/releases/trigger', releaseData, {
  headers: { 
    'Authorization': 'Bearer ' + adminToken,
    'Content-Type': 'application/json'
  },
  timeout: 30000 // 30 second timeout
}).then(response => {
  console.log('✅ Response received:', response.status);
  console.log('Response data:', response.data);
}).catch(error => {
  console.error('❌ Detailed Error Analysis:');
  console.error('Error Code:', error.code);
  console.error('Error Message:', error.message);
  
  if (error.response) {
    console.error('Response Status:', error.response.status);
    console.error('Response Data:', error.response.data);
    console.error('Response Headers:', error.response.headers);
  } else if (error.request) {
    console.error('Request made but no response:', error.request);
  } else {
    console.error('Network/Setup Error:', error);
  }
});
