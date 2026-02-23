@echo off
title The World Stage — Web Launcher
echo.
echo  ============================================
echo   THE WORLD STAGE — Starting Web Server
echo  ============================================
echo.

cd /d "%~dp0"

echo  [0/3] Killing any stale python/node processes on ports 8000 and 5173...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /R ":8000 " ^| findstr "LISTEN"') do (
    taskkill /PID %%a /F /T >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /R ":5173 " ^| findstr "LISTEN"') do (
    taskkill /PID %%a /F /T >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /R ":8000 "') do (
    taskkill /PID %%a /F /T >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /R ":5173 "') do (
    taskkill /PID %%a /F /T >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo  [1/3] Starting FastAPI backend on port 8000...
start "API Server" cmd /k "cd /d "%~dp0" && python -m uvicorn api:app --host 0.0.0.0 --port 8000"

echo  [2/3] Starting React frontend on port 5173...
timeout /t 2 /nobreak >nul
start "Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo  [3/3] Opening browser in 5 seconds...
timeout /t 5 /nobreak >nul
start http://localhost:5173

echo.
echo  Done! Two server windows should be open.
echo  Close those windows to stop the servers.
echo.
pause
