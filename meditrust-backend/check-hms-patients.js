const axios = require('axios');

console.log('Checking HMS patients...\n');

const HMS_BASE_URL = 'http://localhost:4000';

// Get all patients to see what exists
axios.get(`${HMS_BASE_URL}/hms/patients`)
  .then(response => {
    console.log('✅ HMS Patients found:');
    if (response.data.patients && response.data.patients.length > 0) {
      response.data.patients.forEach((patient, i) => {
        console.log(`${i+1}. ID: ${patient.id}, Name: ${patient.patient_name}, Status: ${patient.status}`);
      });
    } else {
      console.log('No patients found in HMS');
    }
  })
  .catch(err => {
    console.log('❌ Failed to get patients:', err.message);
    if (err.response) {
      console.log('Status:', err.response.status);
      console.log('Data:', err.response.data);
    }
  });
