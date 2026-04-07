const prisma = require('./utils/prisma');

// Check campaign 1 details
prisma.campaign.findUnique({
  where: { id: 1 },
  include: { patient: true }
}).then(campaign => {
  console.log('Campaign 1 Details:');
  console.log('===================');
  console.log('ID:', campaign.id);
  console.log('Patient HMS ID:', campaign.patient_hms_id);
  console.log('Patient ID:', campaign.patient_id);
  console.log('Patient Name:', campaign.patient_full_name);
  console.log('Verified Amount:', campaign.verified_amount);
  console.log('Released Amount:', campaign.released_amount);
  console.log('Status:', campaign.status);
  
  if (campaign.patient_hms_id) {
    console.log('\n✅ Campaign HAS HMS patient ID - should update HMS');
  } else {
    console.log('\n❌ Campaign missing HMS patient ID - cannot update HMS');
    console.log('This is why HMS ledger is not updated!');
  }
  
  prisma.$disconnect();
}).catch(err => {
  console.error('Error:', err.message);
});
