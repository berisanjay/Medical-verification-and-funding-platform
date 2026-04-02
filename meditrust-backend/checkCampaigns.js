const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function checkCampaigns() {
  try {
    const campaigns = await prisma.campaign.findMany({ 
      where: { status: 'LIVE_CAMPAIGN' }, 
      select: { id: true, title: true, patient_full_name: true } 
    });
    
    console.log('Live campaigns:');
    campaigns.forEach(c => {
      console.log(`ID: ${c.id}, Title: ${c.title}`);
      console.log(`Patient Name: '${c.patient_full_name}'`);
      console.log('---');
    });
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await prisma.$disconnect();
  }
}

checkCampaigns();
