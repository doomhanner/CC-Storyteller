#!/bin/bash

set -e

echo ""
echo "============================================"
echo "   CC-Storyteller Installation"
echo "============================================"
echo ""

# Change to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==========================================
# Check Prerequisites
# ==========================================

echo "[1/6] Checking prerequisites..."
echo ""

# Check Python
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python 3 is not installed.${NC}"
    echo ""
    echo "Please install Python 3.10 or higher:"
    echo "  macOS:  brew install python@3.11"
    echo "  Ubuntu: sudo apt install python3.11 python3.11-venv"
    echo "  Fedora: sudo dnf install python3.11"
    echo ""
    exit 1
fi

# Check Python version (need 3.10+)
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo -e "${RED}[ERROR] Python 3.10+ required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "  Python $PYTHON_VERSION - ${GREEN}OK${NC}"

# Check Node.js
echo "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}[ERROR] Node.js is not installed.${NC}"
    echo ""
    echo "Please install Node.js 18 or higher:"
    echo "  macOS:  brew install node"
    echo "  Ubuntu: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs"
    echo "  Or use nvm: https://github.com/nvm-sh/nvm"
    echo ""
    exit 1
fi

# Check Node version (need 18+)
NODE_VERSION=$(node --version | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${RED}[ERROR] Node.js 18+ required. Found: $(node --version)${NC}"
    exit 1
fi
echo -e "  Node.js $(node --version) - ${GREEN}OK${NC}"

# Check npm
echo "Checking npm installation..."
if ! command -v npm &> /dev/null; then
    echo -e "${RED}[ERROR] npm is not installed.${NC}"
    exit 1
fi
echo -e "  npm $(npm --version) - ${GREEN}OK${NC}"

echo ""
echo -e "${GREEN}Prerequisites check passed!${NC}"
echo ""

# ==========================================
# Create Virtual Environment
# ==========================================

echo "[2/6] Creating Python virtual environment..."

if [ -d ".venv" ]; then
    echo "  Virtual environment already exists, skipping..."
else
    python3 -m venv .venv
    echo "  Created .venv"
fi
echo ""

# ==========================================
# Install Python Dependencies
# ==========================================

echo "[3/6] Installing Python dependencies..."
echo "  This may take a few minutes..."
echo ""

source .venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -e .
echo ""
echo -e "  ${GREEN}Python dependencies installed!${NC}"
echo ""

# ==========================================
# Install Node Dependencies
# ==========================================

echo "[4/6] Installing frontend dependencies..."
echo ""

cd frontend
npm install
cd ..
echo ""
echo -e "  ${GREEN}Frontend dependencies installed!${NC}"
echo ""

# ==========================================
# Build Frontend
# ==========================================

echo "[5/6] Building frontend..."
echo ""

cd frontend
npm run build
cd ..
echo ""
echo -e "  ${GREEN}Frontend built successfully!${NC}"
echo ""

# ==========================================
# Create .env file
# ==========================================

echo "[6/6] Setting up configuration..."
echo ""

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "  Created .env from template"
    else
        cat > .env << 'EOF'
# CC-Storyteller Environment Variables
# Add your API keys below

# Anthropic API Key (for Claude models)
ANTHROPIC_API_KEY=

# OpenAI API Key (optional)
OPENAI_API_KEY=

# Google API Key (optional)
GOOGLE_API_KEY=
EOF
        echo "  Created .env template"
    fi
else
    echo "  .env already exists, skipping..."
fi

if [ ! -f config.yaml ]; then
    echo "  config.yaml will be created on first run"
fi

echo ""
echo "============================================"
echo -e "   ${GREEN}Installation Complete!${NC}"
echo "============================================"
echo ""
echo "To start CC-Storyteller, run:"
echo "  ./scripts/start.sh"
echo ""
