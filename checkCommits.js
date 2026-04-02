const { execSync } = require('child_process');

try {
  const output = execSync('git log --oneline -10', { encoding: 'utf8' });
  console.log('Recent commits:');
  console.log(output);
} catch (error) {
  console.error('Error:', error.message);
}
