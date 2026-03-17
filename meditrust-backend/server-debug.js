const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');

console.log('🔧 Loading environment variables...');
dotenv.config();

console.log('🔧 Creating Express app...');
const app = express();

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

console.log('🔧 Loading routes...');

try {
  app.use('/api/auth', require('./routes/auth'));
  console.log('✅ Auth route loaded');
} catch (err) {
  console.error('❌ Auth route error:', err.message);
  process.exit(1);
}

try {
  app.use('/api/admin', require('./routes/admin'));
  console.log('✅ Admin route loaded');
} catch (err) {
  console.error('❌ Admin route error:', err.message);
  process.exit(1);
}

try {
  app.use('/api/campaigns', require('./routes/campaigns'));
  console.log('✅ Campaigns route loaded');
} catch (err) {
  console.error('❌ Campaigns route error:', err.message);
  process.exit(1);
}

try {
  app.use('/api/donations', require('./routes/donations'));
  console.log('✅ Donations route loaded');
} catch (err) {
  console.error('❌ Donations route error:', err.message);
  process.exit(1);
}

try {
  app.use('/api/releases', require('./routes/releases'));
  console.log('✅ Releases route loaded');
} catch (err) {
  console.error('❌ Releases route error:', err.message);
  process.exit(1);
}

try {
  app.use('/api/story', require('./routes/story'));
  console.log('✅ Story route loaded');
} catch (err) {
  console.error('❌ Story route error:', err.message);
  process.exit(1);
}

try {
  app.use('/api/suggestions', require('./routes/suggestions'));
  console.log('✅ Suggestions route loaded');
} catch (err) {
  console.error('❌ Suggestions route error:', err.message);
  process.exit(1);
}

try {
  app.use('/internal', require('./routes/internal'));
  console.log('✅ Internal route loaded');
} catch (err) {
  console.error('❌ Internal route error:', err.message);
  process.exit(1);
}

app.get('/', (req, res) => {
  res.json({ message: 'MediTrust Backend Running', status: 'OK' });
});

const PORT = process.env.PORT || 3000;

console.log('🚀 Starting server...');

app.listen(PORT, () => {
  console.log(`✅ MediTrust Backend running on port ${PORT}`);
});

process.on('uncaughtException', (err) => {
  console.error('❌ Uncaught Exception:', err);
  process.exit(1);
});

process.on('unhandledRejection', (err) => {
  console.error('❌ Unhandled Rejection:', err);
  process.exit(1);
});
