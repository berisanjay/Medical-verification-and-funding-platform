const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function checkAllCampaigns() {
  try {
    const campaigns = await prisma.campaign.findMany({ 
      select: { id: true, title: true, patient_full_name: true, status: true } 
    });
    
    console.log('All campaigns:');
    campaigns.forEach(c => {
      console.log(`ID: ${c.id}, Status: ${c.status}, Title: ${c.title}`);
      console.log(`Patient Name: '${c.patient_full_name}'`);
      console.log('---');
    });
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await prisma.$disconnect();
  }
}

checkAllCampaigns();
