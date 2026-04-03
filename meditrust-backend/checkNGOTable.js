const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function checkNGOTable() {
  try {
    console.log('Checking NGO table...');
    
    // Check total count
    const count = await prisma.nGO.count();
    console.log(`Total NGOs in Prisma table: ${count}`);
    
    // Show first NGO structure
    if (count > 0) {
      const firstNGO = await prisma.nGO.findFirst();
      console.log('First NGO structure:', Object.keys(firstNGO));
      console.log('Sample NGO:', firstNGO);
    }
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await prisma.$disconnect();
  }
}

checkNGOTable();
