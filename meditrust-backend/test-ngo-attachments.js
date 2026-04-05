const axios = require('axios');
const jwt = require('jsonwebtoken');

// Create admin token
const adminToken = jwt.sign(
  { id: 3, email: 'gajananberi@gmail.com', role: 'ADMIN' },
  '45e3b99e194a899848cc5a1444782842b8880a659a13cfaeb415d973572a6be05ca9e112d0d1ce9c624979b7606e38f5268d5051c7e1c7ab76871b684b6cac5b'
);

console.log('Testing NGO email with document attachments...');

// Test sending NGO email with documents
axios.post('http://localhost:3000/api/ngo/send-email/1', {
  email_subject: 'Test: NGO Support Request with Documents',
  email_body: 'This email contains patient documents for your review.'
}, {
  headers: { 
    'Authorization': 'Bearer ' + adminToken,
    'Content-Type': 'application/json'
  }
}).then(response => {
  console.log('✅ SUCCESS! NGO email sent with documents');
  console.log('📧 NGO:', response.data.ngo_email);
  console.log('📎 Check server console for attachment details');
  console.log('📄 Response:', response.data);
}).catch(error => {
  console.error('❌ Error:', error.response?.data || error.message);
});
