const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
dotenv.config();

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
app.listen(PORT, () => {
  console.log(`HMS Service running on port ${PORT}`);
});