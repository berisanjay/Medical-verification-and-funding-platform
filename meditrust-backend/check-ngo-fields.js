const prisma = require('./utils/prisma');

// Check if NGOMatch has the required fields
prisma.nGOMatch.findFirst().then(match => {
  if (match) {
    console.log('NGOMatch fields:', Object.keys(match));
    console.log('Has response_token:', 'response_token' in match);
    console.log('Has response_expires_at:', 'response_expires_at' in match);
    console.log('Has notified_at:', 'notified_at' in match);
    console.log('Has responded_at:', 'responded_at' in match);
  } else {
    console.log('No NGO matches found to check fields');
  }
  prisma.$disconnect();
}).catch(err => {
  console.error('Error:', err.message);
});
