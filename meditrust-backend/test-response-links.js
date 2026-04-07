const axios = require('axios');

// Create a new NGO match to test the updated email system
axios.post('http://localhost:3000/api/ngo/match/1', 
  { disease: 'Coronary Artery Disease' },
  {
    headers: { 'x-flask-secret': 'meditrust_flask_internal_2026' }
  }
).then(response => {
  console.log('✅ New NGO match created:', response.data);
  
  if (response.data.ngos && response.data.ngos.length > 0) {
    const newMatchId = response.data.ngos[0].match_id;
    console.log('📧 Testing email with response links for match:', newMatchId);
    
    // Now test sending email with the new response links
    const axios2 = require('axios');
    const jwt = require('jsonwebtoken');
    const adminToken = jwt.sign(
      { id: 3, email: 'gajananberi@gmail.com', role: 'ADMIN' },
      '45e3b99e194a899848cc5a1444782842b8880a659a13cfaeb415d973572a6be05ca9e112d0d1ce9c624979b7606e38f5268d5051c7e1c7ab76871b684b6cac5b'
    );
    
    return axios2.post(`http://localhost:3000/api/ngo/send-email/${newMatchId}`, {
      email_subject: 'UPDATED: NGO Support Request with Response Links',
      email_body: 'This email now includes Accept/Reject buttons for easy response!'
    }, {
      headers: { 
        'Authorization': 'Bearer ' + adminToken,
        'Content-Type': 'application/json'
      }
    });
  }
}).then(response => {
  console.log('🎉 SUCCESS! Email sent with response links');
  console.log('📧 Check your email for Accept/Reject buttons');
  console.log('📄 Response:', response.data);
}).catch(error => {
  console.error('Error:', error.response?.data || error.message);
});
