#!/usr/bin/env bash
set -e

echo "========================================================"
echo "       STOCKLENS - School Exhibition Platform"
echo "   Dual Equity Analytics & Verified Attribution Engine"
echo "========================================================"
echo ""

# 1. Verify Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.11+."
    exit 1
fi

# 2. Verify Node.js & npm
if ! command -v npm &> /dev/null; then
    echo "[ERROR] npm could not be found. Please install Node.js."
    exit 1
fi

# 3. Check and install backend dependencies if needed
echo "[Setup] Checking Python backend dependencies..."
if ! python3 -c "import fastapi, uvicorn, pydantic, dotenv" &> /dev/null; then
    echo "[Setup] Installing backend dependencies from requirements.txt..."
    pip3 install -r backend/requirements.txt
else
    echo "[Setup] Backend dependencies satisfied."
fi

# 4. Check and install frontend dependencies if needed
echo "[Setup] Checking frontend node dependencies..."
if [ ! -d "frontend/node_modules" ]; then
    echo "[Setup] Installing frontend npm dependencies..."
    (cd frontend && npm install)
else
    echo "[Setup] Frontend dependencies satisfied."
fi

echo ""
echo "[1/3] Starting StockLens FastAPI Backend on http://127.0.0.1:8000 ..."
(cd backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) &
BACKEND_PID=$!

echo "[2/3] Starting StockLens React Frontend on http://localhost:5173 ..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT

echo "[3/3] Waiting for servers to initialize..."
sleep 3

echo ""
echo "========================================================"
echo "StockLens Platform is live!"
echo "Web Application: http://localhost:5173"
echo "API Documentation: http://127.0.0.1:8000/docs"
echo "Health Check: http://127.0.0.1:8000/api/health"
echo "Press Ctrl+C to terminate both servers."
echo "========================================================"
echo ""

# Open default browser
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:5173" &> /dev/null &
elif command -v open &> /dev/null; then
    open "http://localhost:5173" &> /dev/null &
fi

wait
