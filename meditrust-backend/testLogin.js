const axios = require('axios');

async function testLogin() {
  try {
    const response = await axios.post('http://localhost:3000/api/admin/login', {
      email: 'gajananberi@gmail.com',
      password: 'Test@1234',
      admin_secret: 'MediTrustAdmin@2026SecretKey'
    });
    
    console.log('✅ Login SUCCESS!');
    console.log('Response:', response.data);
  } catch (error) {
    console.log('❌ Login FAILED!');
    if (error.response) {
      console.log('Status:', error.response.status);
      console.log('Error:', error.response.data);
    } else {
      console.log('Network Error:', error.message);
    }
  }
}

testLogin();
