@echo off
rem Change to the directory of the batch file so it works even if run as Administrator
cd /d "%~dp0"

echo ===================================================
echo Starting GenAI Guard Application...
echo ===================================================

echo [0/5] Activating Virtual Environment...
call venv\Scripts\activate.bat

echo [1/5] Starting LLM Guard Engine...
start "LLM Guard Engine" cmd /k "python services/llm_guard/main.py"

echo [2/5] Starting Main Dashboard...
start "Main Dashboard" cmd /k "python -m uvicorn app.main:app --reload"

echo [3/5] Starting Audio Guard Engine...
start "Audio Guard Engine" cmd /k "cd services\audio_guard & uvicorn main:app --port 8002"

echo [4/5] Starting File Sandbox Microservice...
start "File Sandbox Microservice" cmd /k "cd FileSandbox & uvicorn main:app --port 8003"

echo [5/5] Starting G Mail Sync...
start "Gmail Sync" cmd /k "python -m app.modules.email_guard.gmail_sync"



echo.
echo All components have been launched in separate terminals!
echo You can access the main dashboard at: http://localhost:8000/dashboard
echo ===================================================
