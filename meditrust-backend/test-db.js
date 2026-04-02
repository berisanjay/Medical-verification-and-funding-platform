const prisma = require('./utils/prisma');

console.log('Testing database connection...');

prisma.$connect()
  .then(() => {
    console.log('✅ Database connected successfully');
    return prisma.$disconnect();
  })
  .then(() => {
    console.log('✅ Database disconnected');
    process.exit(0);
  })
  .catch(err => {
    console.error('❌ Database connection error:', err.message);
    console.error('Full error:', err);
    process.exit(1);
  });
