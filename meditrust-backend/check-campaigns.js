const prisma = require('./utils/prisma');

prisma.campaign.findMany({
  where: { status: 'LIVE_CAMPAIGN' },
  select: { id: true, title: true, status: true }
}).then(campaigns => {
  console.log('Live campaigns:', campaigns.length);
  campaigns.forEach(c => console.log(`- ${c.id}: ${c.title}`));
  prisma.$disconnect();
}).catch(err => {
  console.error('Error:', err.message);
});
