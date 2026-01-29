@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================
echo    CC-Storyteller Installation
echo ============================================
echo.

:: Change to project root directory
cd /d "%~dp0.."

:: ==========================================
:: Check Prerequisites
:: ==========================================

echo [1/6] Checking prerequisites...
echo.

:: Check Python
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.10 or higher from:
    echo   https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Check Python version (need 3.10+)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
)

if !PYTHON_MAJOR! LSS 3 (
    echo [ERROR] Python 3.10+ required. Found: !PYTHON_VERSION!
    pause
    exit /b 1
)
if !PYTHON_MAJOR! EQU 3 if !PYTHON_MINOR! LSS 10 (
    echo [ERROR] Python 3.10+ required. Found: !PYTHON_VERSION!
    pause
    exit /b 1
)
echo   Python !PYTHON_VERSION! - OK

:: Check Node.js
echo Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo.
    echo Please install Node.js 18 or higher from:
    echo   https://nodejs.org/
    echo.
    pause
    exit /b 1
)

:: Check Node version (need 18+)
for /f "tokens=1 delims=v" %%v in ('node --version') do set NODE_VERSION_RAW=%%v
for /f "tokens=1 delims=." %%a in ("!NODE_VERSION_RAW!") do set NODE_MAJOR=%%a

:: Handle the 'v' prefix
for /f "tokens=1 delims=." %%a in ('node --version') do (
    set NODE_VER=%%a
    set NODE_VER=!NODE_VER:v=!
)

if !NODE_VER! LSS 18 (
    echo [ERROR] Node.js 18+ required. Found: !NODE_VER!
    pause
    exit /b 1
)
echo   Node.js - OK

:: Check npm
echo Checking npm installation...
npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm is not installed.
    pause
    exit /b 1
)
echo   npm - OK

echo.
echo Prerequisites check passed!
echo.

:: ==========================================
:: Create Virtual Environment
:: ==========================================

echo [2/6] Creating Python virtual environment...

if exist .venv (
    echo   Virtual environment already exists, skipping...
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo   Created .venv
)
echo.

:: ==========================================
:: Install Python Dependencies
:: ==========================================

echo [3/6] Installing Python dependencies...
echo   This may take a few minutes...
echo.

call .venv\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install -e .
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)
echo.
echo   Python dependencies installed!
echo.

:: ==========================================
:: Install Node Dependencies
:: ==========================================

echo [4/6] Installing frontend dependencies...
echo.

cd frontend
call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install Node dependencies.
    cd ..
    pause
    exit /b 1
)
cd ..
echo.
echo   Frontend dependencies installed!
echo.

:: ==========================================
:: Build Frontend
:: ==========================================

echo [5/6] Building frontend...
echo.

cd frontend
call npm run build
if errorlevel 1 (
    echo [ERROR] Failed to build frontend.
    cd ..
    pause
    exit /b 1
)
cd ..
echo.
echo   Frontend built successfully!
echo.

:: ==========================================
:: Create .env file
:: ==========================================

echo [6/6] Setting up configuration...
echo.

if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo   Created .env from template
    ) else (
        echo # CC-Storyteller Environment Variables> .env
        echo # Add your API keys below>> .env
        echo.>> .env
        echo # Anthropic API Key (for Claude models)>> .env
        echo ANTHROPIC_API_KEY=>> .env
        echo.>> .env
        echo # OpenAI API Key (optional)>> .env
        echo OPENAI_API_KEY=>> .env
        echo.>> .env
        echo # Google API Key (optional)>> .env
        echo GOOGLE_API_KEY=>> .env
        echo   Created .env template
    )
) else (
    echo   .env already exists, skipping...
)

if not exist config.yaml (
    echo   config.yaml will be created on first run
)

echo.
echo ============================================
echo    Installation Complete!
echo ============================================
echo.
echo To start CC-Storyteller, run:
echo   scripts\start.bat
echo.
echo Or double-click start.bat in the scripts folder.
echo.
pause
