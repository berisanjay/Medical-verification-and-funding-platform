const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const http = require('node:http');
dotenv.config();

const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));
// Routes
app.use('/api/auth',      require('./routes/auth'));
app.use('/api/admin',     require('./routes/admin'));
app.use('/api/campaigns', require('./routes/campaigns'));
app.use('/api/donations', require('./routes/donations'));
app.use('/api/releases',  require('./routes/releases'));
app.use('/api/story',     require('./routes/story'));
app.use('/api/suggestions', require('./routes/suggestions'));
app.use('/internal',      require('./routes/internal'));

app.get('/', (req, res) => {
  res.json({ message: 'MediTrust Backend Running', status: 'OK' });
});

const PORT = Number.parseInt(process.env.PORT, 10) || 3000;

const server = http.createServer(app);

server.on('error', (err) => {
  if (err && err.code === 'EADDRINUSE') {
    console.error(`ERROR: Port ${PORT} is already in use.`);
    console.error('   Stop the process using it, or change `PORT` in your `.env` (e.g. 3008).');
  } else {
    console.error('ERROR: Failed to start MediTrust Backend:', err);
  }
  process.exit(1);
});

server.listen(PORT, () => {
  console.log(`MediTrust Backend running on port ${PORT}`);
});
