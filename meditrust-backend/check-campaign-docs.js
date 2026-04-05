const prisma = require('./utils/prisma');

prisma.campaign.findUnique({
  where: { id: 1 },
  include: { documents: true }
}).then(campaign => {
  if (campaign && campaign.documents) {
    console.log('Campaign documents:', campaign.documents.length);
    campaign.documents.forEach((doc, i) => {
      console.log(`  ${i+1}. ${doc.document_type}: ${doc.file_name}`);
      console.log(`     Has file_url: ${!!doc.file_url}`);
      console.log(`     Is base64: ${doc.file_url ? doc.file_url.startsWith('data:') : false}`);
    });
  } else {
    console.log('No documents found for campaign 1');
  }
  prisma.$disconnect();
}).catch(err => {
  console.error('Error:', err.message);
});
