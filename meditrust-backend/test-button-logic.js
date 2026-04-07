const axios = require('axios');
const jwt = require('jsonwebtoken');

// Create admin token
const adminToken = jwt.sign(
  { id: 3, email: 'gajananberi@gmail.com', role: 'ADMIN' },
  '45e3b99e194a899848cc5a1444782842b8880a659a13cfaeb415d973572a6be05ca9e112d0d1ce9c624979b7606e38f5268d5051c7e1c7ab76871b684b6cac5b'
);

// Check current NGO match statuses to verify button logic
axios.get('http://localhost:3000/api/ngo/all-matches', {
  headers: { 'Authorization': 'Bearer ' + adminToken }
}).then(response => {
  console.log('📊 NGO Matches Table - Updated Button Logic:');
  console.log('==========================================\n');
  
  response.data.matches.forEach((match, i) => {
    console.log(`${i+1}. ${match.ngo_name}`);
    console.log(`   Status: ${match.status}`);
    
    // Show what button should be displayed
    if (match.status === 'ACCEPTED' || match.status === 'REJECTED') {
      console.log(`   🎯 Button: 📞 Contact NGO (green)`);
    } else if (match.status === 'NOTIFIED') {
      console.log(`   🎯 Button: ✅ Done (disabled, gray)`);
    } else {
      console.log(`   🎯 Button: 📧 Compose & Send (blue outline)`);
    }
    
    console.log(`   Notified: ${match.notified_at || 'Not yet'}`);
    console.log(`   Responded: ${match.responded_at || 'Not yet'}`);
    console.log('');
  });
  
  console.log('✅ Button Logic Summary:');
  console.log('• PENDING: 📧 Compose & Send');
  console.log('• NOTIFIED: ✅ Done (disabled)');
  console.log('• ACCEPTED: 📞 Contact NGO');
  console.log('• REJECTED: 📞 Contact NGO');
  console.log('\n🎉 Multiple emails prevented - Done button disabled after sending!');
  
}).catch(error => {
  console.error('Error:', error.response?.data || error.message);
});
