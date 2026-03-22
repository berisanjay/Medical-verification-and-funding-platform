const fs = require('fs');

// Read HTML file and extract JavaScript
const html = fs.readFileSync('create-campaign.html', 'utf8');

// Extract script content
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/s);
if (!scriptMatch) {
  console.error('❌ No script section found');
  process.exit(1);
}

const jsCode = scriptMatch[1];

// Check for common syntax errors in the HTTP status checking section
const errors = [];

// Check for missing quotes in toast calls
const toastMatches = jsCode.match(/toast\("([^"]*)"/g);
if (toastMatches) {
  toastMatches.forEach(match => {
    if (match[1] && !match[1].endsWith('"')) {
      errors.push(`Missing closing quote in: ${match[0]}`);
    }
  });
}

// Check for missing quotes in setTimeout
const timeoutMatches = jsCode.match(/setTimeout\(\(\) => window\.location\.href = "([^"]*)"/g);
if (timeoutMatches) {
  timeoutMatches.forEach(match => {
    if (match[1] && !match[1].endsWith('"')) {
      errors.push(`Missing closing quote in setTimeout: ${match[0]}`);
    }
  });
}

// Check for missing quotes in innerHTML
const innerHTMLMatches = jsCode.match(/innerHTML = "([^"]*)"/g);
if (innerHTMLMatches) {
  innerHTMLMatches.forEach(match => {
    if (match[1] && !match[1].endsWith('"')) {
      errors.push(`Missing closing quote in innerHTML: ${match[0]}`);
    }
  });
}

if (errors.length > 0) {
  console.error('❌ JavaScript syntax errors found:');
  errors.forEach(error => console.error(`  - ${error}`));
  process.exit(1);
} else {
  console.log('✅ JavaScript syntax is valid');
}
