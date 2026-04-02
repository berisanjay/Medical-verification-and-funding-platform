const { PrismaClient } = require('@prisma/client');
const bcrypt = require('bcryptjs');
const prisma = new PrismaClient();

async function testPassword() {
  try {
    const admin = await prisma.user.findUnique({ where: { email: 'gajananberi@gmail.com' } });
    
    console.log('Testing password for:', admin.email);
    console.log('Stored hash:', admin.password_hash);
    
    const testPassword = 'Test@1234';
    const isValid = await bcrypt.compare(testPassword, admin.password_hash);
    
    console.log('Password to test:', testPassword);
    console.log('Password match:', isValid);
    
    // Let's also test with a fresh hash
    const freshHash = await bcrypt.hash(testPassword, 10);
    console.log('Fresh hash test:', await bcrypt.compare(testPassword, freshHash));
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await prisma.$disconnect();
  }
}

testPassword();
