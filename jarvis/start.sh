#!/bin/bash

# Kill stale python server.py and vite instances
pkill -f "python.*server.py" 2>/dev/null
pkill -f "vite" 2>/dev/null

# Create logs directory if it doesn't exist
mkdir -p logs

echo ""
echo " ============================================"
echo "  J.A.R.V.I.S.  SYSTEM BOOT (macOS)"
echo " ============================================"
echo ""

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment (.venv) not found. Please run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Start Python backend in background
echo " [1/3] Starting backend on port 8340..."
python3 server.py > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready
echo " [2/3] Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8340/api/health >/dev/null; then
        echo " [OK]  Backend is online."
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo "Error: Backend failed to start. Check logs/backend.log"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
done

# Start frontend
echo " [3/3] Starting Vite frontend..."
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Open browser after short delay
sleep 2
open http://localhost:5173

echo ""
echo " ============================================"
echo "  JARVIS IS ONLINE  |  http://localhost:5173"
echo "  Press Ctrl+C to shut down all services."
echo " ============================================"
echo ""

# Clean shutdown function on Ctrl+C
cleanup() {
    echo -e "\nShutting down J.A.R.V.I.S. services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    pkill -f "vite" 2>/dev/null
    exit 0
}
trap cleanup SIGINT

# Tail backend logs to keep script alive and show output
tail -f logs/backend.log
