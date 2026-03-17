const { PrismaClient } = require('@prisma/client');
const dotenv = require('dotenv');

dotenv.config();

console.log('🔧 Testing database connection...');

async function testConnection() {
  try {
    const prisma = new PrismaClient();
    
    console.log('🔧 Prisma client created');
    
    // Test simple query
    const result = await prisma.$queryRaw`SELECT 1`;
    console.log('✅ Database connection successful:', result);
    
    await prisma.$disconnect();
    console.log('✅ Disconnected from database');
    
  } catch (error) {
    console.error('❌ Database connection failed:', error);
    process.exit(1);
  }
}

testConnection();
