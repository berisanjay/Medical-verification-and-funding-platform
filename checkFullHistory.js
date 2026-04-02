const { execSync } = require('child_process');

try {
  console.log('=== Recent commits ===');
  const output = execSync('git log --oneline -10', { encoding: 'utf8' });
  console.log(output);
  
  console.log('\n=== Current status ===');
  const status = execSync('git status', { encoding: 'utf8' });
  console.log(status);
  
  console.log('\n=== Remote branches ===');
  const branches = execSync('git branch -r', { encoding: 'utf8' });
  console.log(branches);
  
} catch (error) {
  console.error('Error:', error.message);
}
