console.log('Starting test server...');

const express = require('express');
const app = express();

app.get('/test', (req, res) => {
  res.json({ message: 'Simple test server working' });
});

const PORT = 3001;
app.listen(PORT, () => {
  console.log(`Test server running on port ${PORT}`);
});
