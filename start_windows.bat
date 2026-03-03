@echo off
REM Startup script for Windows
REM Starts all services in separate windows

echo ========================================
echo Starting Medical Verification System
echo ========================================
echo.

REM Start MongoDB (if installed locally)
echo Starting MongoDB...
start "MongoDB" cmd /k "echo MongoDB Server && mongod"
timeout /t 3

REM Start Flask Backend
echo Starting Flask Backend...
start "Flask API" cmd /k "cd flask-backend && venv\Scripts\activate && echo Flask API Server - http://127.0.0.1:5000 && python app.py"
timeout /t 5

REM Start Node Backend
echo Starting Node.js Backend...
start "Node Server" cmd /k "cd node-backend && echo Node.js Server - http://localhost:3000 && npm start"
timeout /t 3

REM Open Frontend
echo Opening Frontend...
start http://localhost:3000

echo.
echo ========================================
echo All services started!
echo ========================================
echo.
echo Services running:
echo - MongoDB: mongodb://localhost:27017
echo - Flask API: http://127.0.0.1:5000
echo - Node Server: http://localhost:3000
echo - Frontend: http://localhost:3000
echo.
echo Close this window to keep services running
echo Close individual windows to stop services
echo.
pause
