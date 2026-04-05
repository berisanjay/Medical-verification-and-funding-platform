const axios = require('axios');

// Find a live campaign and trigger NGO matching
axios.get('http://localhost:3000/api/campaigns')
  .then(response => {
    const campaigns = response.data.campaigns || [];
    const liveCampaign = campaigns.find(c => c.status === 'LIVE_CAMPAIGN');
    
    if (liveCampaign) {
      console.log('Found live campaign:', liveCampaign.id, liveCampaign.title);
      
      // Trigger NGO matching
      return axios.post(`http://localhost:3000/api/ngo/match/${liveCampaign.id}`, 
        { disease: liveCampaign.title },
        {
          headers: { 'x-flask-secret': 'meditrust_flask_internal_2026' }
        }
      );
    } else {
      console.log('No live campaigns found');
    }
  })
  .then(response => {
    if (response) {
      console.log('NGO matching response:', response.data);
    }
  })
  .catch(error => {
    console.error('Error:', error.response?.data || error.message);
  });
