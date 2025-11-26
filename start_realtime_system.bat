@echo off
echo ⚡ Starting Intradyne Real-Time Trading System...
echo.

:: Check if using Docker or native
if exist "docker-compose.yml" (
    echo 🐳 Docker mode detected
    docker-compose up -d
    timeout /t 5
    echo ✅ Backend services started (Redis, PostgreSQL, API)
    echo 🌐 Opening dashboard...
    timeout /t 2
    start http://localhost:8501
) else (
    echo 🔧 Native mode - Starting services...
    
    :: Start Redis (if installed)
    where redis-server >nul 2>&1
    if %ERRORLEVEL%==0 (
        start "Redis" cmd /k "redis-server"
        echo ✅ Redis started
    ) else (
        echo ⚠️  Redis not found - running in file mode
    )
    
    :: Start API Backend
    start "Intradyne API" cmd /k "cd /d %~dp0 && python -m uvicorn src.api.api_server:app --host 0.0.0.0 --port 8000 --reload"
    echo ✅ API Backend starting on port 8000...
    timeout /t 5
    
    :: Start Streamlit Dashboard
    start "Intradyne Dashboard" cmd /k "cd /d %~dp0 && streamlit run src/interface/streamlit_app.py"
    echo ✅ Dashboard starting on port 8501...
    timeout /t 3
    
    echo.
    echo 🚀 Intradyne is now running!
    echo 📊 Dashboard: http://localhost:8501
    echo 🔌 API Docs: http://localhost:8000/docs
)
