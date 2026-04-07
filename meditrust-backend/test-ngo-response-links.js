const axios = require('axios');
const jwt = require('jsonwebtoken');

// Create admin token
const adminToken = jwt.sign(
  { id: 3, email: 'gajananberi@gmail.com', role: 'ADMIN' },
  '45e3b99e194a899848cc5a1444782842b8880a659a13cfaeb415d973572a6be05ca9e112d0d1ce9c624979b7606e38f5268d5051c7e1c7ab76871b684b6cac5b'
);

// Test sending email to an existing NGO match with the new response links
axios.post('http://localhost:3000/api/ngo/send-email/2', {
  email_subject: 'UPDATED: NGO Support Request with Response Links',
  email_body: 'This email now includes Accept/Reject buttons for easy response!'
}, {
  headers: { 
    'Authorization': 'Bearer ' + adminToken,
    'Content-Type': 'application/json'
  }
}).then(response => {
  console.log('🎉 SUCCESS! Email sent with response links');
  console.log('📧 Check your email for Accept/Reject buttons');
  console.log('📄 Response:', response.data);
  console.log('✅ The email should now include:');
  console.log('   - Custom email body');
  console.log('   - Document attachments');
  console.log('   - Accept/Reject buttons with token links');
  console.log('   - 7-day expiry notice');
}).catch(error => {
  console.error('Error:', error.response?.data || error.message);
});
