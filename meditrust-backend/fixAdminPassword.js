const { PrismaClient } = require('@prisma/client');
const bcrypt = require('bcryptjs');
const prisma = new PrismaClient();

async function fixPassword() {
  try {
    const adminEmail = "gajananberi@gmail.com";
    const password = "Test@1234";
    
    // Create proper hash
    const hashedPassword = await bcrypt.hash(password, 10);
    console.log('New hash:', hashedPassword);
    
    // Update admin user
    const updated = await prisma.user.update({
      where: { email: adminEmail },
      data: { 
        password_hash: hashedPassword,
        role: "ADMIN",
        otp_verified: true
      }
    });
    
    console.log('✅ Admin password fixed!');
    console.log('Email:', updated.email);
    console.log('Name:', updated.name);
    console.log('Role:', updated.role);
    
    // Test the new password
    const testValid = await bcrypt.compare(password, updated.password_hash);
    console.log('Password test:', testValid ? '✅ PASS' : '❌ FAIL');
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await prisma.$disconnect();
  }
}

fixPassword();
