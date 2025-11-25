@echo off
echo Checking for Python...
python --version
if %errorlevel% neq 0 (
    echo Python is not installed or not in your PATH.
    echo Please install Python 3.10+ from python.org and ensure "Add Python to PATH" is checked.
    pause
    exit /b
)

echo Installing dependencies...
pip install -r requirements.txt

echo Ingesting Knowledge Base...
python -m scripts.ingest_knowledge

echo Starting Backend...
start "INTRADYNE Backend" python main.py

echo Setup Complete. Backend is running in a new window.
pause
