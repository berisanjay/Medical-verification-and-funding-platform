require('dotenv').config();

const express = require('express');
const cors = require('cors');

const app = express();

app.use(cors({
  origin: '*',
  methods: ['GET','POST','PUT','DELETE','OPTIONS','PATCH'],
  allowedHeaders: ['Content-Type','Authorization','x-flask-secret']
}));

app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

// Only load NGO routes
app.use('/api/ngo', require('./routes/ngo'));

app.get('/', (req, res) => {
  res.json({ message: 'MediTrust Backend Running', status: 'OK' });
});

const PORT = Number.parseInt(process.env.PORT, 10) || 3000;

const server = require('http').createServer(app);

server.on('error', (err) => {
  if (err && err.code === 'EADDRINUSE') {
    console.error(`ERROR: Port ${PORT} is already in use.`);
    console.error('   Stop the process using it, or change `PORT` in your `.env` (e.g. 3008).');
  }
});

server.listen(PORT, () => {
  console.log(`MediTrust Backend running on port ${PORT}`);
});
