console.log('=== NGO RESPONSE TOKENS AND URLS ===');

const tokens = [
  {
    matchId: 1,
    ngoId: 3,
    token: '7641983a5a656a8a99568cb7a9b214386cfd1ccf6e18b75c1673e6463b508657',
    status: 'NOTIFIED',
    expires: '2026-04-11T12:08:48.249Z'
  },
  {
    matchId: 2,
    ngoId: 4,
    token: '2c186dbf90fa3f7d9a60450a7151cfc39017e04761d0478fbb2bf6bb8c5fed6c',
    status: 'NOTIFIED',
    expires: '2026-04-10T16:57:44.716Z'
  }
];

tokens.forEach((t, index) => {
  console.log(`\n=== NGO MATCH ${index + 1} ===`);
  console.log(`Match ID: ${t.matchId}`);
  console.log(`NGO ID: ${t.ngoId}`);
  console.log(`Status: ${t.status}`);
  console.log(`Token: ${t.token}`);
  console.log(`Expires: ${t.expires}`);
  
  console.log('\n=== RESPONSE URLS ===');
  const approveUrl = `http://localhost:8080/ngo-respond.html?token=${t.token}&action=approve`;
  const rejectUrl = `http://localhost:8080/ngo-respond.html?token=${t.token}&action=reject`;
  
  console.log(`Approve: ${approveUrl}`);
  console.log(`Reject: ${rejectUrl}`);
  
  console.log('\n=== HOW TO TEST ===');
  console.log('1. Start client server: cd client && python -m http.server 8080');
  console.log('2. Open the URLs above in browser');
  console.log('3. Or click the links in the NGO email');
  console.log('---');
});

console.log('\n=== HOW TO GET NEW TOKENS ===');
console.log('1. Go to admin dashboard: http://localhost:8080/client/admin/dashboard.html');
console.log('2. Login with: gajananberi@gmail.com / Admin@123');
console.log('3. Go to NGO Matches section');
console.log('4. Click "Compose & Send" on any match');
console.log('5. New token will be generated and sent via email');
console.log('6. Check database for new token using the query above');
