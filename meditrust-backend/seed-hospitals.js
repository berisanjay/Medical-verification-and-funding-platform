const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  console.log('Seeding hospitals...');

  await prisma.accessibleHospital.upsert({
    where : { id: 1 },
    update: {},
    create: {
      name            : 'Apollo Hospitals Vizag',
      name_aliases    : ['Apollo Hospitals, Vizag','Apollo Hospitals Visakhapatnam','APOLLO HOSPITALS VIZAG','Apollo Heart Institutes'],
      city            : 'Visakhapatnam',
      state           : 'Andhra Pradesh',
      pincode         : '530002',
      address         : 'Waltair Main Road, Visakhapatnam - 530002',
      is_hms_connected: true,
      hms_api_url     : 'http://localhost:4000'
    }
  });
  console.log('✅ Apollo Hospitals Vizag');

  await prisma.accessibleHospital.upsert({
    where : { id: 2 },
    update: {},
    create: {
      name            : 'Apollo Hospitals Jubilee Hills',
      name_aliases    : ['Apollo Hospitals, Jubilee Hills','Apollo Hospitals Hyderabad'],
      city            : 'Hyderabad',
      state           : 'Telangana',
      pincode         : '500033',
      address         : 'Jubilee Hills, Hyderabad - 500033',
      is_hms_connected: true,
      hms_api_url     : 'http://localhost:4000'
    }
  });
  console.log('✅ Apollo Hospitals Jubilee Hills');

  await prisma.accessibleHospital.upsert({
    where : { id: 3 },
    update: {},
    create: {
      name            : 'Government General Hospital Guntur',
      name_aliases    : ['GGH Guntur','Govt General Hospital Guntur'],
      city            : 'Guntur',
      state           : 'Andhra Pradesh',
      pincode         : '522004',
      is_hms_connected: false
    }
  });
  console.log('✅ Govt General Hospital Guntur (Type B)');

  console.log('\nDone! Run: node seed-hospitals.js');
}

main().catch(console.error).finally(() => prisma.$disconnect());