@echo off
echo ========================================
echo Starting Paper Trading Monitor
echo ========================================
echo.
echo This will keep paper trading running 24/7
echo Auto-restart on crashes
echo.

cd /d "%~dp0.."

echo Starting monitor...
python scripts\monitor_paper_trading.py

pause
