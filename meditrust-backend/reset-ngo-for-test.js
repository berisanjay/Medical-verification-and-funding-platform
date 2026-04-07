const prisma = require('./utils/prisma');

// Reset NGO matches to PENDING for testing
console.log('Resetting NGO matches to PENDING status...\n');

prisma.nGOMatch.updateMany({
  where: { status: 'ACCEPTED' },
  data: {
    status: 'PENDING',
    responded_at: null,
    response_token: null,
    response_expires_at: null,
    ngo_response_comment: null
  }
}).then(result => {
  console.log(`Reset ${result.count} NGO matches to PENDING`);
  
  // Check current status
  return prisma.nGOMatch.findMany({
    where: { campaign_id: 1 },
    select: {
      id: true,
      ngo_id: true,
      status: true,
      response_token: true,
      response_expires_at: true
    },
    orderBy: { id: 'desc' }
  });
}).then(matches => {
  console.log('\nCurrent NGO Match Statuses:');
  console.log('============================');
  
  matches.forEach((match, i) => {
    console.log(`${i+1}. Match ID: ${match.id}, NGO ID: ${match.ngo_id}`);
    console.log(`   Status: ${match.status}`);
    console.log(`   Token: ${match.response_token ? 'Present' : 'Null'}`);
    console.log('');
  });
  
  console.log('Now you can:');
  console.log('1. Send fresh NGO emails from admin dashboard');
  console.log('2. Click Accept/Reject links - should work without errors!');
  console.log('3. Check admin dashboard for status updates');
  
  prisma.$disconnect();
}).catch(err => {
  console.error('Error:', err.message);
});
