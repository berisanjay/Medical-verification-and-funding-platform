const prisma = require('./utils/prisma');

prisma.user.findFirst({ where: { role: 'ADMIN' } }).then(admin => {
  if (admin) {
    console.log('Admin found:', { id: admin.id, email: admin.email, name: admin.name });
  } else {
    console.log('No admin user found');
  }
  prisma.$disconnect();
}).catch(err => {
  console.error('Error:', err.message);
});
