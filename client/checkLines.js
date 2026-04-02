const fs = require('fs');
const content = fs.readFileSync('upload.html', 'utf8');
const lines = content.split('\n');
console.log('Line 752:', JSON.stringify(lines[751]));
console.log('Line 753:', JSON.stringify(lines[752]));
console.log('Line 754:', JSON.stringify(lines[753]));
console.log('Line 755:', JSON.stringify(lines[754]));
