const axios = require('axios');

console.log('Testing HMS connection with correct port...\n');

const HMS_BASE_URL = 'http://localhost:4001';

// Test HMS basic connection
axios.get(`${HMS_BASE_URL}/`)
  .then(response => {
    console.log('✅ HMS is running on port 4001!');
    console.log('Response:', response.data);
  })
  .catch(err => {
    console.log('❌ HMS connection failed:', err.message);
  });

// Test HMS patients endpoint
setTimeout(() => {
  console.log('\nTesting HMS patients endpoint...');
  axios.get(`${HMS_BASE_URL}/hms/patients`)
    .then(response => {
      console.log('✅ HMS patients endpoint working!');
      console.log('Patients count:', response.data.patients?.length || 0);
      if (response.data.patients && response.data.patients.length > 0) {
        response.data.patients.forEach((patient, i) => {
          console.log(`${i+1}. ID: ${patient.id}, Name: ${patient.patient_name}, Status: ${patient.status}`);
        });
      }
    })
    .catch(err => {
      console.log('❌ HMS patients failed:', err.message);
      if (err.response) {
        console.log('Status:', err.response.status);
        console.log('Data:', err.response.data);
      }
    });
}, 1000);
