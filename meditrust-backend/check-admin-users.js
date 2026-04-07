const prisma = require('./utils/prisma');

// Check what admin users exist
prisma.user.findMany({
  where: { role: 'ADMIN' },
  select: { id: true, email: true, name: true }
}).then(admins => {
  console.log('Admin users in database:');
  console.log('========================');
  
  if (admins.length === 0) {
    console.log('No admin users found!');
  } else {
    admins.forEach(admin => {
      console.log(`ID: ${admin.id}, Email: ${admin.email}, Name: ${admin.name}`);
    });
  }
  
  prisma.$disconnect();
}).catch(err => {
  console.error('Error:', err.message);
});
