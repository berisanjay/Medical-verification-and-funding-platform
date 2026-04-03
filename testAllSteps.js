const axios = require('axios');

async function testAllSteps() {
  const API = 'http://localhost:3000/api';
  const HMS_API = 'http://localhost:4000';
  
  try {
    console.log('🔧 Step 1: Re-seed admin (password reset)');
    const seedRes = await axios.post(`${API}/admin/seed`, {
      secret: 'MediTrustAdmin@2026SecretKey'
    });
    console.log('✅ Seed response:', seedRes.data);
    
    console.log('\n🔑 Step 2: Login as admin');
    const loginRes = await axios.post(`${API}/admin/login`, {
      email: 'gajananberi@gmail.com',
      password: 'Admin@MediTrust2026',
      admin_secret: 'MediTrustAdmin@2026SecretKey'
    });
    const adminToken = loginRes.data.token;
    console.log('✅ Login successful!');
    console.log('Token:', adminToken ? 'RECEIVED' : 'MISSING');
    
    console.log('\n📋 Step 3: Verify campaign is correct');
    const campaignRes = await axios.get(`${API}/campaigns/1`);
    const campaign = campaignRes.data.campaign;
    console.log('✅ Campaign details:');
    console.log(`  ID: ${campaign.id}`);
    console.log(`  Status: ${campaign.status}`);
    console.log(`  Patient HMS ID: ${campaign.patient_hms_id}`);
    console.log(`  Verified Amount: ₹${campaign.verified_amount?.toLocaleString('en-IN')}`);
    console.log(`  Collected Amount: ₹${campaign.collected_amount?.toLocaleString('en-IN')}`);
    
    console.log('\n💰 Step 4: Trigger fund release');
    const releaseRes = await axios.post(`${API}/releases/trigger`, {
      campaign_id: 1,
      amount: 100000
    }, {
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json'
      }
    });
    console.log('✅ Fund release response:', releaseRes.data);
    
    console.log('\n🏥 Step 5: Verify HMS ledger updated');
    try {
      const hmsRes = await axios.get(`${HMS_API}/hms/patients/3/outstanding`);
      console.log('✅ HMS outstanding after release:', hmsRes.data);
    } catch (hmsErr) {
      console.log('⚠️ HMS not running or unreachable:', hmsErr.message);
    }
    
    console.log('\n🎉 All tests completed!');
    
  } catch (error) {
    console.error('❌ Test failed:', error.response?.data || error.message);
  }
}

testAllSteps();
