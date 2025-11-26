@echo off
title Intradyne 24/7 Supervisor
echo ==================================================
echo      INTRADYNE 24/7 TRADING SYSTEM LAUNCHER
echo ==================================================
echo.
echo Starting Supervisor...
echo This will manage the Trading Bot and Dashboard.
echo Close this window to stop the system.
echo.

cd /d "%~dp0.."
python scripts/supervisor.py

pause
