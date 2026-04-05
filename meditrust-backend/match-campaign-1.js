const axios = require('axios');

axios.post('http://localhost:3000/api/ngo/match/1', 
  { disease: 'Coronary Artery Disease' },
  {
    headers: { 'x-flask-secret': 'meditrust_flask_internal_2026' }
  }
).then(response => {
  console.log('NGO matching response:', response.data);
}).catch(error => {
  console.error('Error:', error.response?.data || error.message);
});
