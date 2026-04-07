const axios = require('axios');

console.log('Testing HMS payment creation...\n');

// Test direct HMS payment call
axios.post('http://localhost:4000/hms/payments', {
  patient_hms_id: 3,
  amount: 50000,
  source: 'MediTrust Crowdfunding',
  notes: 'Test payment integration'
}).then(response => {
  console.log('✅ HMS Payment Response:');
  console.log('Success:', response.data.success);
  console.log('Payment ID:', response.data.payment?.id);
  console.log('Updated Ledger:', response.data.updated_ledger);
  
  if (response.data.success) {
    console.log('\n🎉 HMS integration working!');
    console.log('• Amount Paid:', response.data.updated_ledger.amount_paid);
    console.log('• Outstanding:', response.data.updated_ledger.outstanding_amount);
  }
}).catch(error => {
  console.error('❌ HMS Payment Error:');
  if (error.response) {
    console.log('Status:', error.response.status);
    console.log('Error:', error.response.data);
  } else {
    console.log('Message:', error.message);
  }
});
