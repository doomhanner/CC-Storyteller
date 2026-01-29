@echo off
setlocal enabledelayedexpansion

:: Change to project root directory
cd /d "%~dp0.."

:: Check if installation has been run
if not exist .venv (
    echo.
    echo [ERROR] CC-Storyteller is not installed.
    echo Please run install.bat first.
    echo.
    pause
    exit /b 1
)

:: Check if frontend is built
if not exist frontend\dist (
    echo.
    echo [ERROR] Frontend has not been built.
    echo Please run install.bat first.
    echo.
    pause
    exit /b 1
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Check if this is first run (no API keys configured)
set FIRST_RUN=0
if not exist .env (
    set FIRST_RUN=1
) else (
    :: Check if .env has any API key set
    findstr /r "^ANTHROPIC_API_KEY=." .env >nul 2>&1
    if errorlevel 1 (
        findstr /r "^OPENAI_API_KEY=." .env >nul 2>&1
        if errorlevel 1 (
            set FIRST_RUN=1
        )
    )
)

:: Determine URL to open
set URL=http://localhost:8000
if !FIRST_RUN! EQU 1 (
    set URL=http://localhost:8000/setup
)

echo.
echo ============================================
echo    CC-Storyteller
echo ============================================
echo.
echo Starting server at !URL!
echo Press Ctrl+C to stop.
echo.

:: Open browser after a short delay (in background)
start /b cmd /c "timeout /t 2 /nobreak >nul && start !URL!"

:: Start the server
storyteller serve --host 127.0.0.1 --port 8000
