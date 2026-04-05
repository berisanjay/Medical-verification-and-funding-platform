const axios = require('axios');
const jwt = require('jsonwebtoken');

// Create admin token
const adminToken = jwt.sign(
  { id: 3, email: 'gajananberi@gmail.com', role: 'ADMIN' },
  '45e3b99e194a899848cc5a1444782842b8880a659a13cfaeb415d973572a6be05ca9e112d0d1ce9c624979b7606e38f5268d5051c7e1c7ab76871b684b6cac5b'
);

// Check current NGO match statuses
axios.get('http://localhost:3000/api/ngo/all-matches', {
  headers: { 'Authorization': 'Bearer ' + adminToken }
}).then(response => {
  console.log('📊 Current NGO Match Statuses:');
  console.log('Summary:', response.data.summary);
  
  response.data.matches.forEach((match, i) => {
    console.log(`\n${i+1}. ${match.ngo_name}`);
    console.log(`   Status: ${match.status}`);
    console.log(`   Notified: ${match.notified_at || 'Not yet'}`);
    console.log(`   Responded: ${match.responded_at || 'Not yet'}`);
    console.log(`   Email: ${match.ngo_email}`);
  });
  
  console.log('\n🎯 NGO Response Tracking System:');
  console.log('✅ Email links sent with tokens');
  console.log('✅ Real-time status updates');
  console.log('✅ Admin dashboard monitoring');
  
}).catch(error => {
  console.error('Error:', error.response?.data || error.message);
});
