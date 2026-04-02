// seed-ngo.js — Run this in meditrust-backend folder
// Command: node seed-ngo.js

const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const ngos = [
  {
    name            : 'Genesis Foundation',
    email           : 'contact@genesis-foundation.net',
    phone           : '+91 9681767118',
    city            : 'New Delhi',
    state           : 'Delhi',
    specializations : {
      disease_cardiac: true,
      disease_cancer: false,
      disease_neuro: false,
      disease_kidney: false,
      disease_liver: false,
      disease_orthopedic: false,
      disease_eye: false,
      disease_rare: false,
      disease_general: true,
      supports_children: true,
      supports_adults: true,
      supports_elderly: false,
      states_covered: ['All'],
      income_limit: 300000,
      max_grant: 1500000
    },
    is_active           : true,
    is_verified         : true,
    notes               : 'Pan India. Cardiac + General. Strong CSR network.'
  },
  {
    name            : 'YouWeCan Foundation',
    email           : 'contact@youwecan.org',
    phone           : '+91 92680 68050',
    city            : 'Chandigarh',
    state           : 'Punjab',
    specializations : {
      disease_cardiac: false,
      disease_cancer: true,
      disease_neuro: false,
      disease_kidney: false,
      disease_liver: false,
      disease_orthopedic: false,
      disease_eye: false,
      disease_rare: false,
      disease_general: false,
      supports_children: true,
      supports_adults: true,
      supports_elderly: false,
      states_covered: ['All'],
      income_limit: 400000,
      max_grant: 1000000
    },
    is_verified    : true
  },
  {
    name            : 'CanKids KidsCan',
    email           : 'contact@cankidsindia.org',
    phone           : '+91-11-40512467',
    city            : 'New Delhi',
    state           : 'Delhi',
    specializations : {
      disease_cardiac: false,
      disease_cancer: true,
      disease_neuro: false,
      disease_kidney: false,
      disease_liver: false,
      disease_orthopedic: false,
      disease_eye: false,
      disease_rare: false,
      disease_general: false,
      supports_children: true,
      supports_adults: false,
      supports_elderly: false,
      states_covered: [
        'Delhi', 'Maharashtra', 'Karnataka', 'Tamil Nadu',
        'Telangana', 'Andhra Pradesh', 'West Bengal', 'Gujarat',
        'Rajasthan', 'Punjab', 'Haryana', 'Uttar Pradesh',
        'Madhya Pradesh', 'Kerala', 'Odisha', 'Bihar',
        'Jharkhand', 'Assam', 'Uttarakhand', 'Himachal Pradesh',
        'Goa', 'Chhattisgarh'
      ],
      income_limit: 350000,
      max_grant: 1200000
    },
    is_verified    : true
  },
  {
    name            : 'Indian Cancer Society',
    email           : 'contact@indiancancersociety.org',
    phone           : '+91 11 49424723',
    city            : 'Mumbai',
    state           : 'Maharashtra',
    specializations : {
      disease_cardiac: false,
      disease_cancer: true,
      disease_neuro: false,
      disease_kidney: false,
      disease_liver: false,
      disease_orthopedic: false,
      disease_eye: false,
      disease_rare: false,
      disease_general: false,
      supports_children: true,
      supports_adults: true,
      supports_elderly: true,
      states_covered: ['All'],
      income_limit: 400000,
      max_grant: 800000
    },
    is_verified    : true
  },
  {
    name            : 'Sri Sathya Sai Sanjeevani',
    email           : 'info@sssanjeevani.in',
    phone           : '+91-7888729707',
    city            : 'Raipur',
    state           : 'Chhattisgarh',
    specializations : {
      disease_cardiac: true,
      disease_cancer: false,
      disease_neuro: false,
      disease_kidney: false,
      disease_liver: false,
      disease_orthopedic: false,
      disease_eye: false,
      disease_rare: false,
      disease_general: false,
      supports_children: true,
      supports_adults: false,
      supports_elderly: false,
      states_covered: [
        'Chhattisgarh', 'Madhya Pradesh',
        'Maharashtra', 'Karnataka', 'Telangana'
      ],
      income_limit: 300000,
      max_grant: 1500000
    },
    is_verified    : true
  },
  {
    name            : 'Child Vision Foundation',
    email           : 'info@childvisionfoundation.in',
    phone           : '+91 98677 64560',
    city            : 'Mumbai',
    state           : 'Maharashtra',
    specializations : {
      disease_cardiac: false,
      disease_cancer: true,
      disease_neuro: false,
      disease_kidney: false,
      disease_liver: false,
      disease_orthopedic: false,
      disease_eye: false,
      disease_rare: false,
      disease_general: false,
      supports_children: true,
      supports_adults: false,
      supports_elderly: false,
      states_covered: [
        'Maharashtra', 'Delhi', 'Rajasthan', 'Gujarat',
        'Uttar Pradesh', 'West Bengal', 'Karnataka', 'Tamil Nadu',
        'Andhra Pradesh', 'Telangana', 'Kerala', 'Punjab',
        'Haryana', 'Odisha', 'Bihar', 'Jharkhand',
        'Chhattisgarh', 'Assam', 'Uttarakhand', 'Himachal Pradesh',
        'Goa', 'Madhya Pradesh'
      ],
      income_limit: 350000,
      max_grant: 1100000
    },
    is_verified    : true
  },
  {
    name            : 'St. Jude Childcare Centres',
    email           : 'contact@stjudechild.org',
    phone           : '+91 22 6666 3152',
    city            : 'Chennai',
    state           : 'Tamil Nadu',
    specializations : {
      disease_cardiac: false,
      disease_cancer: true,
      disease_neuro: false,
      disease_kidney: false,
      disease_liver: false,
      disease_orthopedic: false,
      disease_eye: false,
      disease_rare: false,
      disease_general: false,
      supports_children: true,
      supports_adults: false,
      supports_elderly: false,
      states_covered: [
        'Tamil Nadu', 'Maharashtra', 'Delhi', 'Karnataka', 'Kerala'
      ],
      income_limit: 400000,
      max_grant: 1300000
    },
    is_verified    : true
  },
  {
    name            : 'Child Help Foundation',
    email           : 'contact@childhelpfoundationindia.org',
    phone           : '+91 22 28118588',
    city            : 'Mumbai',
    state           : 'Maharashtra',
    specializations : {
      disease_cardiac: true,
      disease_cancer: true,
      disease_neuro: true,
      disease_kidney: true,
      disease_liver: true,
      disease_orthopedic: true,
      disease_eye: true,
      disease_rare: true,
      disease_general: true,
      supports_children: true,
      supports_adults: true,
      supports_elderly: false,
      states_covered: ['All'],
      income_limit: 300000,
      max_grant: 900000
    },
    is_verified    : true
  },
  {
    name            : 'Vatsalya Foundation',
    email           : 'info@vatsalyango.org',
    phone           : '+91-80-2543 7171',
    city            : 'Bangalore',
    state           : 'Karnataka',
    specializations : {
      disease_cardiac: true,
      disease_cancer: false,
      disease_neuro: false,
      disease_kidney: false,
      disease_liver: false,
      disease_orthopedic: false,
      disease_eye: false,
      disease_rare: false,
      disease_general: false,
      supports_children: true,
      supports_adults: false,
      supports_elderly: false,
      states_covered: ['Karnataka', 'Andhra Pradesh', 'Telangana'],
      income_limit: 250000,
      max_grant: 1000000
    },
    is_verified    : true
  },
  {
    name            : 'Saving Hearts India',
    email           : 'icare@saveheartsfoundation.org',
    phone           : '+91 7506400647',
    city            : 'Mumbai',
    state           : 'Maharashtra',
    specializations : {
      disease_cardiac: true,
      disease_cancer: false,
      disease_neuro: false,
      disease_kidney: false,
      disease_liver: false,
      disease_orthopedic: false,
      disease_eye: false,
      disease_rare: false,
      disease_general: false,
      supports_children: true,
      supports_adults: true,
      supports_elderly: true,
      states_covered: ['Maharashtra', 'Delhi', 'Gujarat', 'Rajasthan'],
      income_limit: 350000,
      max_grant: 1200000
    },
    is_verified    : true
  },
];

async function seedNGOs() {
  console.log('\n🌱 Seeding NGO database...\n');
  let seeded = 0;
  let skipped = 0;

  for (const ngo of ngos) {
    try {
      const existing = await prisma.nGO.findFirst({
        where: { email: ngo.email }
      });

      if (existing) {
        console.log(`  ⏭️  Already exists: ${ngo.name}`);
        skipped++;
        continue;
      }

      await prisma.nGO.create({ data: ngo });
      console.log(`  ✅ Seeded: ${ngo.name}`);
      seeded++;

    } catch (err) {
      console.error(`  ❌ Failed: ${ngo.name} — ${err.message}`);
    }
  }

  console.log(`\n✅ Done! Seeded: ${seeded} | Skipped: ${skipped}\n`);
  await prisma.$disconnect();
}

seedNGOs().catch(e => {
  console.error('Seed failed:', e);
  process.exit(1);
});