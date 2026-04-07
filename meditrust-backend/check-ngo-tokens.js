const prisma = require('./utils/prisma');

// Check current NGO match statuses and tokens
prisma.nGOMatch.findMany({
  where: { campaign_id: 1 },
  select: {
    id: true,
    ngo_id: true,
    status: true,
    response_token: true,
    response_expires_at: true,
    notified_at: true,
    responded_at: true
  },
  orderBy: { id: 'desc' }
}).then(matches => {
  console.log('NGO Match Statuses:');
  console.log('====================\n');
  
  matches.forEach((match, i) => {
    console.log(`${i+1}. Match ID: ${match.id}`);
    console.log(`   NGO ID: ${match.ngo_id}`);
    console.log(`   Status: ${match.status}`);
    console.log(`   Token: ${match.response_token ? 'Present' : 'Null/Used'}`);
    console.log(`   Expires: ${match.response_expires_at || 'N/A'}`);
    console.log(`   Notified: ${match.notified_at || 'Not yet'}`);
    console.log(`   Responded: ${match.responded_at || 'Not yet'}`);
    console.log('');
  });
  
  // Check if any tokens are still valid
  const now = new Date();
  const validTokens = matches.filter(m => 
    m.response_token && 
    m.response_expires_at && 
    new Date(m.response_expires_at) > now &&
    ['PENDING', 'NOTIFIED'].includes(m.status)
  );
  
  console.log(`Valid tokens available: ${validTokens.length}`);
  if (validTokens.length > 0) {
    console.log('Test links:');
    validTokens.forEach(m => {
      const baseUrl = 'http://localhost:3000/api/ngo/respond';
      console.log(`  NGO ${m.ngo_id}:`);
      console.log(`    Accept: ${baseUrl}?token=${m.response_token}&status=ACCEPTED`);
      console.log(`    Reject: ${baseUrl}?token=${m.response_token}&status=REJECTED`);
    });
  }
  
  prisma.$disconnect();
}).catch(err => {
  console.error('Error:', err.message);
});
