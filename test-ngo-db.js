const mysql = require('mysql2/promise');

console.log('Testing NGO DB connection...');

const pool = mysql.createPool({
  host    : process.env.NGO_DB_HOST     || 'localhost',
  user    : process.env.NGO_DB_USER     || 'root',
  password: process.env.NGO_DB_PASSWORD || '',
  database: process.env.NGO_DB_NAME     || 'ngo_db',
  waitForConnections: true,
  connectionLimit   : 10
});

pool.getConnection()
  .then(conn => {
    console.log('✅ NGO DB connection successful');
    conn.release();
  })
  .catch(err => {
    console.error('❌ NGO DB connection failed:', err.message);
  })
  .finally(() => {
    pool.end();
  });
