const axios = require('axios');
const jwt = require('jsonwebtoken');

console.log('Creating fresh NGO match with valid response links...\n');

// First, create a new NGO match
axios.post('http://localhost:3000/api/ngo/match/1', 
  { disease: 'Coronary Artery Disease' },
  {
    headers: { 'x-flask-secret': 'meditrust_flask_internal_2026' }
  }
).then(response => {
  console.log('NGO Match Response:', response.data);
  
  if (response.data.ngos && response.data.ngos.length > 0) {
    const newMatch = response.data.ngos[0];
    console.log(`\nNew match created: ${newMatch.match_id}`);
    
    // Now send email to get fresh token
    const adminToken = jwt.sign(
      { id: 3, email: 'gajananberi@gmail.com', role: 'ADMIN' },
      '45e3b99e194a899848cc5a1444782842b8880a659a13cfaeb415d973572a6be05ca9e112d0d1ce9c624979b7606e38f5268d5051c7e1c7ab76871b684b6cac5b'
    );
    
    return axios.post(`http://localhost:3000/api/ngo/send-email/${newMatch.match_id}`, {
      email_subject: 'Fresh NGO Support Request - Test Response Links',
      email_body: 'This is a fresh email with valid response links for testing.'
    }, {
      headers: { 
        'Authorization': 'Bearer ' + adminToken,
        'Content-Type': 'application/json'
      }
    });
  } else {
    console.log('No new NGOs matched (they already exist)');
    
    // Find an existing PENDING match and send email
    const adminToken = jwt.sign(
      { id: 3, email: 'gajananberi@gmail.com', role: 'ADMIN' },
      '45e3b99e194a899848cc5a1444782842b8880a659a13cfaeb415d973572a6be05ca9e112d0d1ce9c624979b7606e38f5268d5051c7e1c7ab76871b684b6cac5b'
    );
    
    // Send email to match ID 2 (should be PENDING)
    return axios.post('http://localhost:3000/api/ngo/send-email/2', {
      email_subject: 'NGO Support Request - Fresh Token',
      email_body: 'Testing NGO response links with fresh token.'
    }, {
      headers: { 
        'Authorization': 'Bearer ' + adminToken,
        'Content-Type': 'application/json'
      }
    });
  }
}).then(response => {
  console.log('\nEmail sent successfully!');
  console.log('Response:', response.data);
  console.log('\nNow check the server console for the token details...');
  console.log('The NGO email should contain fresh Accept/Reject links.');
}).catch(error => {
  console.error('Error:', error.response?.data || error.message);
});
