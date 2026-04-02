const { execSync } = require('child_process');

try {
  const output = execSync('git show origin/master:client/admin/dashboard.html', { encoding: 'utf8' });
  console.log('First 50 lines of latest dashboard.html:');
  console.log(output.split('\n').slice(0, 50).join('\n'));
} catch (error) {
  console.error('Error:', error.message);
}
