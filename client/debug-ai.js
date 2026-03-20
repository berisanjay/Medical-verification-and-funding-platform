// Debug script for AI verification issues
// Paste this in browser console on create-campaign page

console.log('🔍 Starting AI Debug...');

// Check token
const token = localStorage.getItem('patientToken');
console.log('🔑 Token:', token ? 'EXISTS' : 'MISSING');

// Check documents
const docs = window.docs || {};
console.log('📄 Documents:', {
  aadh: !!docs.aadh,
  ration: !!docs.ration, 
  income: !!docs.income,
  estimate: !!docs.estimate,
  summary: !!docs.summary
});

// Check API endpoints
const API = 'http://localhost:3000/api';
console.log('🌐 API endpoint:', API);

// Test API connectivity
fetch(`${API}/health`)
  .then(r => r.json())
  .then(d => console.log('✅ API Health:', d))
  .catch(e => console.error('❌ API Down:', e));

// Test Flask connectivity
fetch('http://localhost:5000/health')
  .then(r => r.json())
  .then(d => console.log('✅ Flask Health:', d))
  .catch(e => console.error('❌ Flask Down:', e));

console.log('🔍 Debug complete. Check results above.');
