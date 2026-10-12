@echo off
TITLE StockLens Launcher
echo ========================================================
echo        STOCKLENS - School Exhibition Platform
echo    Dual Equity Analytics & Verified Attribution Engine
echo ========================================================
echo.

REM 1. Verify Python Installation
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not found in PATH! Please install Python 3.11+.
    pause
    exit /b 1
)

REM 2. Verify Node.js & npm Installation
node --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not found in PATH! Please install Node.js 18+.
    pause
    exit /b 1
)

REM 3. Install Backend Dependencies if needed
echo [Setup] Checking backend Python dependencies...
python -c "import fastapi, uvicorn, pydantic, dotenv" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [Setup] Installing backend dependencies from requirements.txt...
    pip install -r backend\requirements.txt
) else (
    echo [Setup] Backend dependencies already satisfied.
)

REM 4. Install Frontend Dependencies if needed
echo [Setup] Checking frontend node modules...
if not exist "frontend\node_modules\" (
    echo [Setup] Installing frontend npm dependencies...
    cd frontend
    call npm install
    cd ..
) else (
    echo [Setup] Frontend node_modules found.
)

echo.
echo [1/3] Launching StockLens FastAPI Backend on http://127.0.0.1:8000 ...
start "StockLens Backend (FastAPI :8000)" cmd /k "cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/3] Launching StockLens React Frontend on http://localhost:5173 ...
start "StockLens Frontend (Vite :5173)" cmd /k "cd frontend && npm run dev"

echo [3/3] Waiting for servers to initialize...
timeout /t 3 >nul

echo.
echo ========================================================
echo StockLens Platform is live!
echo Web Application: http://localhost:5173
echo API Documentation: http://127.0.0.1:8000/docs
echo Health Check: http://127.0.0.1:8000/api/health
echo ========================================================
echo.

REM Open default browser
start http://localhost:5173
pause
