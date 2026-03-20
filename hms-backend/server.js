const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
dotenv.config();

// Add error handling
process.on('uncaughtException', (err) => {
  console.error('Uncaught Exception:', err);
  process.exit(1);
});

process.on('unhandledRejection', (err) => {
  console.error('Unhandled Rejection:', err);
  process.exit(1);
});

const app = express();
app.use(cors());
app.use(express.json());

// Routes
app.use('/hms/hospitals', require('./routes/hospitals'));
app.use('/hms/patients', require('./routes/patients'));
app.use('/hms/payments', require('./routes/payments'));


app.get('/', (req, res) => {
  res.json({ message: 'HMS Service Running', status: 'OK' });
});

const PORT = process.env.PORT || 4000;
const server = app.listen(PORT, () => {
  console.log(`HMS Service running on port ${PORT}`);
});

// Handle server errors
server.on('error', (err) => {
  console.error('Server error:', err);
  process.exit(1);
});

// Keep process alive
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  server.close(() => {
    console.log('Process terminated');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully');
  server.close(() => {
    console.log('Process terminated');
    process.exit(0);
  });
});