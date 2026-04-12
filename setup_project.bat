@echo off
echo ==================================================
echo       GenAi-Guard Automated Setup Wizard
echo ==================================================
echo.

echo [1/4] Checking Python Virtual Environment (venv)...
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created successfully!
) else (
    echo Virtual environment already exists. Skipping creation...
)
echo.

echo [2/4] Activating venv and installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo Dependencies installed successfully!
echo.

echo [3/4] Downloading massive AI Models from Hugging Face...
echo (Depending on your internet speed, this might take a few minutes)
python scripts\download_hf_models.py
echo.

echo [4/4] Building the File Sandbox Docker container...
echo Please ensure Docker Desktop is running on your machine.
cd FileSandbox
docker build -t sandbox-image .
cd ..
echo.

echo ==================================================
echo  Setup Complete! You are fully equipped to run.
echo  To launch all services, double-click start_app.bat
echo ==================================================
pause
