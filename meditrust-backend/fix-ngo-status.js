const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function fixNGOStatuses() {
  try {
    console.log('Fixing NGO match statuses...');
    
    // Update all NGO matches that have NOTIFIED status but no responded_at
    const result = await prisma.nGOMatch.updateMany({
      where: {
        status: 'NOTIFIED',
        responded_at: null
      },
      data: {
        status: 'PENDING'
      }
    });
    
    console.log(`Updated ${result.count} NGO matches from NOTIFIED to PENDING`);
    
    // Also check current status distribution
    const counts = await prisma.nGOMatch.groupBy({
      by: ['status'],
      _count: true
    });
    
    console.log('\nCurrent NGO match status distribution:');
    counts.forEach(c => {
      console.log(`  ${c.status}: ${c._count}`);
    });
    
  } catch(err) {
    console.error('Error:', err);
  } finally {
    await prisma.$disconnect();
  }
}

fixNGOStatuses();
