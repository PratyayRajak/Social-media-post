#!/bin/bash
echo "============================"
echo "  PostAll (Python) - Setup & Run"
echo "============================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed!"
    echo "Install it from: https://python.org"
    exit 1
fi

echo "[OK] Python found: $(python3 --version)"
echo ""

# Check if Node.js is installed (for frontend)
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js is not installed! (needed for frontend)"
    echo "Download it from: https://nodejs.org"
    exit 1
fi

echo "[OK] Node.js found: $(node -v)"
echo ""

# Install Python dependencies
echo "[1/3] Installing Python backend dependencies..."
cd backend_python
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
cd ..
echo ""

echo "[2/3] Installing frontend dependencies..."
cd frontend && npm install && cd ..
echo ""

echo "============================"
echo "  Starting PostAll..."
echo "============================"
echo ""

# Start backend in background
cd backend_python
source venv/bin/activate
python server.py &
BACKEND_PID=$!
cd ..

# Start frontend
echo "Starting frontend..."
cd frontend
npm run dev

# Cleanup on exit
kill $BACKEND_PID 2>/dev/null
