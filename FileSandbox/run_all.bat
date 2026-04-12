@echo off
echo =========================================
echo Setting up File Analysis Sandbox (Windows)
echo =========================================

echo 1. Checking for Python...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo 2. Checking for Docker...
docker ps >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo.
echo 3. Creating Python Virtual Environment (venv)...
if not exist "venv\" (
    python -m venv venv
)
echo Virtual environment ready.

echo.
echo 4. Activating venv and installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo.
echo 5. Building Docker Sandbox Image...
docker build -t sandbox-image .

echo.
echo 6. Starting FastAPI Server in a separate window...
start "FastAPI Server" cmd /k "call venv\Scripts\activate.bat && echo Starting Uvicorn... && uvicorn main:app --reload"

echo.
echo Waiting 5 seconds for the server to start up...
timeout /t 5 /nobreak > nul

echo.
echo 7. Running Test Script...
python test_script.py

echo.
echo =========================================
echo Test Complete! 
echo The API server is still running in the new window.
echo You can close both windows when you are done.
echo =========================================
pause
