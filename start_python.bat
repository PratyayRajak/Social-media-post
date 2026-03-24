@echo off
echo ============================
echo   PostAll (Python) - Setup ^& Run
echo ============================
echo.

:: Check if Python is installed
where py >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo Download it from: https://python.org
    pause
    exit /b
)

echo [OK] Python found:
py --version
echo.

:: Check if Node.js is installed (for frontend)
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed! (needed for frontend)
    echo Download it from: https://nodejs.org
    pause
    exit /b
)

echo [OK] Node.js found:
node -v
echo.

:: Install Python dependencies
echo [1/3] Installing Python backend dependencies...
cd backend_python
if not exist venv (
    py -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt
cd ..
echo.

echo [2/3] Installing frontend dependencies...
cd frontend
call npm install
cd ..
echo.

echo ============================
echo   Starting PostAll...
echo ============================
echo.

:: Start backend in background
start "PostAll Backend (Python)" cmd /c "cd backend_python && venv\Scripts\activate.bat && py server.py"

:: Start frontend
echo Starting frontend...
cd frontend
npm run dev
