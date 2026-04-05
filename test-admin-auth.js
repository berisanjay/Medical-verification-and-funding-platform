const http = require('http');

const options = {
  hostname: 'localhost',
  port: 3000,
  path: '/api/admin/dashboard',
  method: 'GET',
  headers: {
    'Authorization': 'Bearer test-admin-token'
  }
};

const req = http.request(options, (res) => {
  console.log('STATUS:', res.statusCode);
  
  let data = '';
  res.on('data', (chunk) => {
    data += chunk;
  });
  
  res.on('end', () => {
    console.log('BODY:', data);
  });
});

req.on('error', (err) => {
  console.error('REQUEST ERROR:', err);
});

req.end();

console.log('Testing admin dashboard endpoint...');
