#!/bin/bash

# Change to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Check if installation has been run
if [ ! -d ".venv" ]; then
    echo ""
    echo -e "${RED}[ERROR] CC-Storyteller is not installed.${NC}"
    echo "Please run ./scripts/install.sh first."
    echo ""
    exit 1
fi

# Check if frontend is built
if [ ! -d "frontend/dist" ]; then
    echo ""
    echo -e "${RED}[ERROR] Frontend has not been built.${NC}"
    echo "Please run ./scripts/install.sh first."
    echo ""
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if this is first run (no API keys configured)
FIRST_RUN=0
if [ ! -f .env ]; then
    FIRST_RUN=1
else
    # Check if .env has any API key set (non-empty value after =)
    if ! grep -qE '^ANTHROPIC_API_KEY=.+' .env 2>/dev/null && \
       ! grep -qE '^OPENAI_API_KEY=.+' .env 2>/dev/null; then
        FIRST_RUN=1
    fi
fi

# Determine URL to open
URL="http://localhost:8000"
if [ "$FIRST_RUN" -eq 1 ]; then
    URL="http://localhost:8000/setup"
fi

echo ""
echo "============================================"
echo "   CC-Storyteller"
echo "============================================"
echo ""
echo "Starting server at $URL"
echo "Press Ctrl+C to stop."
echo ""

# Open browser after a short delay (in background)
(
    sleep 2
    # Detect OS and open browser
    case "$(uname -s)" in
        Linux*)
            if command -v xdg-open &> /dev/null; then
                xdg-open "$URL" 2>/dev/null
            elif command -v gnome-open &> /dev/null; then
                gnome-open "$URL" 2>/dev/null
            fi
            ;;
        Darwin*)
            open "$URL" 2>/dev/null
            ;;
    esac
) &

# Start the server
storyteller serve --host 127.0.0.1 --port 8000
