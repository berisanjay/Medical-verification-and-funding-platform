const prisma = require('./utils/prisma');

// Show the actual response links sent to NGOs
prisma.nGOMatch.findMany({
  where: { status: 'NOTIFIED' },
  include: {
    campaign: { select: { title: true, patient_full_name: true } }
  }
}).then(matches => {
  console.log('🔗 NGO Response Links (sent via email):');
  console.log('=====================================\n');
  
  matches.forEach((match, i) => {
    const baseUrl = 'http://localhost:3000/api/ngo/respond';
    const acceptLink = `${baseUrl}?token=${match.response_token}&status=ACCEPTED`;
    const rejectLink = `${baseUrl}?token=${match.response_token}&status=REJECTED`;
    
    console.log(`${i+1}. ${match.campaign.title}`);
    console.log(`   Token: ${match.response_token}`);
    console.log(`   ✅ Accept: ${acceptLink}`);
    console.log(`   ❌ Reject: ${rejectLink}`);
    console.log(`   ⏰ Expires: ${match.response_expires_at}`);
    console.log('');
  });
  
  console.log('🎯 How NGOs Can Respond:');
  console.log('1. Click Accept/Reject buttons in email');
  console.log('2. Links open directly in browser');
  console.log('3. Status updates instantly in admin dashboard');
  console.log('4. Tokens expire after 7 days');
  
  prisma.$disconnect();
}).catch(err => {
  console.error('Error:', err.message);
});
