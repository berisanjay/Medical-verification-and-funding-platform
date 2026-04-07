const { PrismaClient } = require('@prisma/client');
const dotenv = require('dotenv');

// Load HMS environment
dotenv.config({ path: '../hms-backend/.env' });

console.log('HMS DATABASE_URL:', process.env.DATABASE_URL);

// Connect to HMS database
const hmsPrisma = new PrismaClient({
  datasources: {
    db: {
      url: process.env.DATABASE_URL
    }
  }
});

console.log('Checking HMS database for patient ID 3...\n');

hmsPrisma.patient.findUnique({
  where: { id: 3 },
  include: { ledger: true }
}).then(patient => {
  if (patient) {
    console.log('✅ HMS Patient Found:');
    console.log('ID:', patient.id);
    console.log('Name:', patient.patient_name);
    console.log('Status:', patient.status);
    
    if (patient.ledger) {
      console.log('• Total Estimate:', patient.ledger.total_estimate);
      console.log('• Amount Paid:', patient.ledger.amount_paid);
      console.log('• Outstanding:', patient.ledger.outstanding_amount);
    }
  } else {
    console.log('❌ Patient ID 3 not found in HMS database');
    console.log('This is why HMS payments are failing!');
  }
  
  hmsPrisma.$disconnect();
}).catch(err => {
  console.error('HMS Database Error:', err.message);
});
