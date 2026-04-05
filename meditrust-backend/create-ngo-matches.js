const prisma = require('./utils/prisma');

async function createNGOMatches() {
  try {
    console.log('Creating NGO matches for campaign 1...');
    
    // Check if matches already exist
    const existing = await prisma.nGOMatch.findMany({
      where: { campaign_id: 1 }
    });
    
    if (existing.length > 0) {
      console.log('NGO matches already exist:', existing.length);
      return;
    }
    
    // Create mock NGO matches
    const matches = [
      { campaign_id: 1, ngo_id: 1, status: 'PENDING', match_score: 85 },
      { campaign_id: 1, ngo_id: 2, status: 'PENDING', match_score: 75 },
      { campaign_id: 1, ngo_id: 3, status: 'PENDING', match_score: 90 }
    ];
    
    for (const match of matches) {
      await prisma.nGOMatch.create({ data: match });
      console.log(`Created NGO match for NGO ${match.ngo_id}`);
    }
    
    console.log('NGO matches created successfully!');
    
  } catch (error) {
    console.error('Error creating NGO matches:', error);
  } finally {
    await prisma.$disconnect();
  }
}

createNGOMatches();
