const prisma = require('./utils/prisma');

prisma.nGOMatch.findMany({
  include: {
    campaign: {
      select: {
        id: true,
        title: true,
        patient_full_name: true,
        status: true
      }
    }
  },
  orderBy: { created_at: 'desc' },
  take: 100
}).then(matches => {
  console.log('NGO matches found:', matches.length);
  matches.forEach(m => {
    console.log(`- Match ${m.id}: Campaign ${m.campaign_id}, NGO ${m.ngo_id}, Status: ${m.status}`);
  });
  prisma.$disconnect();
}).catch(err => {
  console.error('Error:', err.message);
});
