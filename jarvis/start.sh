#!/usr/bin/env bash
# JARVIS Startup Script for macOS / Linux
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

mkdir -p logs

echo "============================================"
echo " J.A.R.V.I.S. SYSTEM BOOT (macOS)"
echo "============================================"

# ── Kill stale instances ────────────────────────
echo "[1/4] Checking and clearing ports 8340 & 5173..."
lsof -ti :8340 | xargs kill -9 2>/dev/null || true
lsof -ti :5173 | xargs kill -9 2>/dev/null || true

# ── Start backend ───────────────────────────────
echo "[2/4] Starting backend on port 8340..."
PYTHON_BIN="./venv/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

nohup "$PYTHON_BIN" server.py > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# ── Wait for backend ────────────────────────────
echo "[3/4] Waiting for backend to be ready..."
for i in {1..30}; do
    if /usr/bin/nc -z 127.0.0.1 8340 2>/dev/null; then
        echo "[OK] Backend is online."
        break
    fi
    sleep 0.5
done

# ── Start frontend ──────────────────────────────
echo "[4/4] Starting frontend dev server on port 5173..."
cd frontend
nohup npx vite --host < /dev/null > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

for i in {1..30}; do
    if /usr/bin/nc -z 127.0.0.1 5173 2>/dev/null; then
        echo "[OK] Frontend is online at http://localhost:5173"
        break
    fi
    sleep 0.5
done

cd ..

echo "============================================"
echo " JARVIS IS ONLINE | http://localhost:5173"
echo "============================================"

# Open in default web browser
open http://localhost:5173
