@echo off
title JARVIS — Starting...
color 0B

echo.
echo  ============================================
echo   J.A.R.V.I.S.  SYSTEM BOOT
echo  ============================================
echo.

:: ── Kill any stale instances ────────────────
taskkill /f /im python.exe >nul 2>&1

:: ── Activate venv ───────────────────────────
call .venv\Scripts\activate.bat

:: ── Start Python backend in background ──────
echo  [1/2] Starting backend on port 8340...
start /b "" .venv\Scripts\python.exe server.py > logs\backend.log 2>&1

:: ── Wait for backend to be ready ────────────
echo  [2/2] Waiting for backend...
:wait
ping 127.0.0.1 -n 2 >nul
netstat -ano | findstr ":8340" | findstr "LISTENING" >nul
if errorlevel 1 goto wait
echo  [OK]  Backend is online.

:: ── Start frontend ──────────────────────────
echo  [3/4] Starting frontend dev server...
cd frontend
start /b "" npm run dev > ..\logs\frontend.log 2>&1

:: ── Boot J.A.R.V.I.S. Desktop Container ──────────
echo  [4/4] Booting Electron desktop container...
ping 127.0.0.1 -n 5 >nul
start /b "" npm run electron > ..\logs\electron.log 2>&1

echo.
echo  ============================================
echo   JARVIS IS ONLINE  ^|  http://localhost:5173
echo   Press Ctrl+C to shut everything down.
echo  ============================================
echo.

:: ── Tail backend logs so user sees activity ─
cd ..
powershell -Command "Get-Content logs\backend.log -Wait -Tail 20"
