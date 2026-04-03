const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function fixExistingCampaign() {
  try {
    console.log('🔧 Fixing existing campaign...');
    
    // Update campaign with correct HMS data
    const updated = await prisma.campaign.update({
      where: { id: 1 },
      data: {
        patient_hms_id: 3,
        verified_amount: 933000
      }
    });
    
    console.log('✅ Campaign updated successfully!');
    console.log(`ID: ${updated.id}`);
    console.log(`Patient HMS ID: ${updated.patient_hms_id}`);
    console.log(`Verified Amount: ₹${updated.verified_amount.toLocaleString('en-IN')}`);
    
  } catch (error) {
    console.error('❌ Error updating campaign:', error.message);
  } finally {
    await prisma.$disconnect();
  }
}

fixExistingCampaign();
