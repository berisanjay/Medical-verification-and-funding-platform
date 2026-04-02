const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('🔧 Starting comprehensive server debug...');

// Create log file
const logFile = path.join(__dirname, 'server-debug.log');
const logStream = fs.createWriteStream(logFile, { flags: 'w' });

logStream.write(`=== SERVER DEBUG STARTED AT ${new Date().toISOString()} ===\n`);

// Override console methods to also write to file
const originalConsole = {
  log: console.log,
  error: console.error,
  warn: console.warn,
  info: console.info
};

console.log = (...args) => {
  originalConsole.log(...args);
  logStream.write(`[LOG] ${new Date().toISOString()} - ${args.join(' ')}\n`);
};

console.error = (...args) => {
  originalConsole.error(...args);
  logStream.write(`[ERROR] ${new Date().toISOString()} - ${args.join(' ')}\n`);
};

console.warn = (...args) => {
  originalConsole.warn(...args);
  logStream.write(`[WARN] ${new Date().toISOString()} - ${args.join(' ')}\n`);
};

console.info = (...args) => {
  originalConsole.info(...args);
  logStream.write(`[INFO] ${new Date().toISOString()} - ${args.join(' ')}\n`);
};

// Handle all process events
process.on('uncaughtException', (error) => {
  console.error('💥 UNCAUGHT EXCEPTION:', error);
  logStream.write(`💥 UNCAUGHT EXCEPTION: ${error.stack}\n`);
  logStream.end();
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('💥 UNHANDLED REJECTION:', reason);
  logStream.write(`💥 UNHANDLED REJECTION: ${reason}\nPromise: ${promise}\n`);
  logStream.end();
  process.exit(1);
});

process.on('SIGINT', () => {
  console.log('📡 SIGINT received (Ctrl+C)');
  logStream.write('📡 SIGINT received (Ctrl+C)\n');
  logStream.end();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('📡 SIGTERM received');
  logStream.write('📡 SIGTERM received\n');
  logStream.end();
  process.exit(0);
});

// Check environment
console.log('🔍 Environment check:');
console.log('Node version:', process.version);
console.log('Platform:', process.platform);
console.log('Working directory:', process.cwd());
console.log('Script directory:', __dirname);

// Check .env file
const envPath = path.join(__dirname, '.env');
if (fs.existsSync(envPath)) {
  console.log('✅ .env file exists');
  const envContent = fs.readFileSync(envPath, 'utf8');
  console.log('📝 .env file size:', envContent.length, 'bytes');
  console.log('📝 .env line count:', envContent.split('\n').length);
} else {
  console.log('❌ .env file NOT found');
}

// Check package.json
const pkgPath = path.join(__dirname, 'package.json');
if (fs.existsSync(pkgPath)) {
  const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
  console.log('📦 Package name:', pkg.name);
  console.log('📦 Package version:', pkg.version);
  console.log('📦 Dependencies:', Object.keys(pkg.dependencies || {}));
}

// Check node_modules
const nodeModulesPath = path.join(__dirname, 'node_modules');
if (fs.existsSync(nodeModulesPath)) {
  console.log('✅ node_modules exists');
  try {
    const modules = fs.readdirSync(nodeModulesPath);
    console.log('📦 Installed modules count:', modules.length);
    console.log('📦 Key modules:', ['express', 'cors', 'dotenv', 'prisma', '@prisma/client'].filter(m => modules.includes(m)));
  } catch (e) {
    console.error('❌ Error reading node_modules:', e.message);
  }
} else {
  console.log('❌ node_modules NOT found - run npm install');
}

// Try to load each dependency individually
console.log('🔍 Testing individual module loads...');

const modules = ['express', 'cors', 'dotenv', '@prisma/client'];
for (const mod of modules) {
  try {
    require(mod);
    console.log(`✅ ${mod} - OK`);
  } catch (e) {
    console.error(`❌ ${mod} - FAILED:`, e.message);
  }
}

// Now try to start the actual server
console.log('🚀 Attempting to start server...');

try {
  // Start server with detailed error tracking
  const serverProcess = spawn('node', ['server.js'], {
    cwd: __dirname,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, DEBUG: 'true' }
  });

  serverProcess.stdout.on('data', (data) => {
    const output = data.toString();
    console.log('📤 SERVER STDOUT:', output);
    logStream.write(`[STDOUT] ${new Date().toISOString()} - ${output}`);
  });

  serverProcess.stderr.on('data', (data) => {
    const output = data.toString();
    console.error('📤 SERVER STDERR:', output);
    logStream.write(`[STDERR] ${new Date().toISOString()} - ${output}`);
  });

  serverProcess.on('error', (error) => {
    console.error('💥 SERVER PROCESS ERROR:', error);
    logStream.write(`💥 SERVER PROCESS ERROR: ${error}\n`);
    logStream.end();
  });

  serverProcess.on('close', (code, signal) => {
    console.log(`📤 SERVER PROCESS CLOSED - Code: ${code}, Signal: ${signal}`);
    logStream.write(`📤 SERVER PROCESS CLOSED - Code: ${code}, Signal: ${signal}\n`);
    logStream.end();
  });

  // Set a timeout to see if it stays alive
  setTimeout(() => {
    if (!serverProcess.killed) {
      console.log('✅ Server is still running after 5 seconds');
      logStream.write('✅ Server is still running after 5 seconds\n');
    }
  }, 5000);

  console.log('🔍 Server process started with PID:', serverProcess.pid);
  logStream.write(`🔍 Server process started with PID: ${serverProcess.pid}\n`);

} catch (error) {
  console.error('💥 FAILED TO START SERVER:', error);
  logStream.write(`💥 FAILED TO START SERVER: ${error.stack}\n`);
  logStream.end();
  process.exit(1);
}
