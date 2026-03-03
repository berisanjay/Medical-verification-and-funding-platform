#!/bin/bash
# Startup script for Linux/macOS
# Medical Document Verification System

echo "========================================"
echo "Starting Medical Verification System"
echo "========================================"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down services..."
    kill $FLASK_PID $NODE_PID 2>/dev/null
    echo "Services stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if MongoDB is running
if ! pgrep -x mongod > /dev/null; then
    echo "⚠ MongoDB is not running"
    echo "Start MongoDB with:"
    echo "  Linux: sudo systemctl start mongodb"
    echo "  macOS: brew services start mongodb-community"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start Flask Backend
echo "Starting Flask Backend..."
cd flask-backend
source venv/bin/activate
python app.py &
FLASK_PID=$!
echo "✓ Flask API started (PID: $FLASK_PID) - http://127.0.0.1:5000"
deactivate
cd ..

# Wait for Flask to be ready
sleep 5

# Start Node Backend
echo "Starting Node.js Backend..."
cd node-backend
npm start &
NODE_PID=$!
echo "✓ Node Server started (PID: $NODE_PID) - http://localhost:3000"
cd ..

# Wait for Node to be ready
sleep 3

echo ""
echo "========================================"
echo "All services started!"
echo "========================================"
echo ""
echo "Services:"
echo "  Flask API:   http://127.0.0.1:5000"
echo "  Node Server: http://localhost:3000"
echo "  Frontend:    http://localhost:3000"
echo ""
echo "Process IDs:"
echo "  Flask: $FLASK_PID"
echo "  Node:  $NODE_PID"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Open browser (optional)
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:3000 &
elif command -v open &> /dev/null; then
    open http://localhost:3000 &
fi

# Keep script running
wait
