@echo off
title The World Stage — Web Launcher
echo.
echo  ============================================
echo   THE WORLD STAGE — Starting Web Server
echo  ============================================
echo.

cd /d "%~dp0"

echo  [1/2] Starting FastAPI backend on port 8000...
start "API Server" cmd /k "cd /d "%~dp0" && uvicorn api:app --reload --port 8000"

echo  [2/2] Starting React frontend on port 5173...
timeout /t 2 /nobreak >nul
start "Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo  [3/3] Opening browser in 5 seconds...
timeout /t 5 /nobreak >nul
start http://localhost:5173

echo.
echo  Done! Two server windows should be open.
echo  Close those windows to stop the servers.
echo.
pause
