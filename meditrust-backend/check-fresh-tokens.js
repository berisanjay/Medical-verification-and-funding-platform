const prisma = require('./utils/prisma');

// Check for fresh tokens after the new email
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
  console.log('Updated NGO Match Statuses:');
  console.log('============================\n');
  
  matches.forEach((match, i) => {
    console.log(`${i+1}. Match ID: ${match.id}`);
    console.log(`   NGO ID: ${match.ngo_id}`);
    console.log(`   Status: ${match.status}`);
    console.log(`   Token: ${match.response_token ? 'Present' : 'Null/Used'}`);
    if (match.response_token) {
      console.log(`   Token Value: ${match.response_token}`);
    }
    console.log(`   Expires: ${match.response_expires_at || 'N/A'}`);
    console.log(`   Notified: ${match.notified_at || 'Not yet'}`);
    console.log(`   Responded: ${match.responded_at || 'Not yet'}`);
    console.log('');
  });
  
  // Find valid tokens
  const now = new Date();
  const validTokens = matches.filter(m => 
    m.response_token && 
    m.response_expires_at && 
    new Date(m.response_expires_at) > now &&
    ['PENDING', 'NOTIFIED'].includes(m.status)
  );
  
  console.log(`\nValid tokens available: ${validTokens.length}`);
  if (validTokens.length > 0) {
    console.log('Fresh Test Links:');
    validTokens.forEach(m => {
      const baseUrl = 'http://localhost:3000/api/ngo/respond';
      console.log(`\n  NGO ${m.ngo_id} (Match ${m.id}):`);
      console.log(`    Accept: ${baseUrl}?token=${m.response_token}&status=ACCEPTED`);
      console.log(`    Reject: ${baseUrl}?token=${m.response_token}&status=REJECTED`);
      console.log(`    Expires: ${m.response_expires_at}`);
    });
    console.log('\nThese links should work now! Try clicking the Accept link.');
  }
  
  prisma.$disconnect();
}).catch(err => {
  console.error('Error:', err.message);
});
