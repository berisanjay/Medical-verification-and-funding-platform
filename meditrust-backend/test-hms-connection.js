const axios = require('axios');

console.log('Testing HMS connection...\n');

const HMS_BASE_URL = 'http://localhost:4000';

// Test HMS basic connection
axios.get(`${HMS_BASE_URL}/health`)
  .then(response => {
    console.log('✅ HMS is running!');
    console.log('Response:', response.data);
  })
  .catch(err => {
    console.log('❌ HMS connection failed:', err.message);
    console.log('HMS might not be running on port 4000');
  });

// Test HMS patient status endpoint (used in fund release)
setTimeout(() => {
  console.log('\nTesting HMS patient status endpoint...');
  axios.get(`${HMS_BASE_URL}/hms/patients/1/status`)
    .then(response => {
      console.log('✅ HMS patient status working!');
      console.log('Response:', response.data);
    })
    .catch(err => {
      console.log('❌ HMS patient status failed:', err.message);
      if (err.response) {
        console.log('Status:', err.response.status);
        console.log('Data:', err.response.data);
      }
    });
}, 1000);
