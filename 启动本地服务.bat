@echo off
chcp 65001 >nul 2>nul
setlocal enabledelayedexpansion

echo ========================================
echo   xiaot-menu - Start Local Server
echo ========================================
echo.

set "PYTHON=C:\Users\gyq\.workbuddy\binaries\python\versions\3.13.12\python.exe"
set "APPDIR=%~dp0server"
set "APPFILE=%~dp0server\app.py"

REM Check Python exists
if not exist "%PYTHON%" (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)

REM Check app.py exists via dynamic path
if not exist "!APPFILE!" (
    echo [ERROR] app.py not found!
    echo APPDIR=!APPDIR!
    echo APPFILE=!APPFILE!
    pause
    exit /b 1
)

echo [INFO] Starting backend server...
echo [INFO] After startup visit: http://localhost:8080
echo [INFO] Close this window to stop the server
echo ========================================
echo.

cd /d "!APPDIR!"
"%PYTHON%" "!APPFILE!"

echo.
echo [INFO] Server stopped.
pause
