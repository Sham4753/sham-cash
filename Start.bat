@echo off
cd /d "%~dp0app"
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1
start "" /B pythonw.exe server.py
timeout /t 5 /nobreak >nul
taskkill /f /im msedge.exe >nul 2>&1
timeout /t 1 /nobreak >nul
start msedge --app=http://127.0.0.1:8080