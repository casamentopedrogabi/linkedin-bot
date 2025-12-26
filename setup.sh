#!/bin/bash

# =========================
# Base directory (absolute)
# =========================
BASE_DIR="/c/Users/pedro/.vscode/bot"
cd "$BASE_DIR" || exit 1

# =========================
# Colors
# =========================
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}=========================================${NC}"
echo -e "${CYAN}  LINKEDIN BOT v2.0 - AUTO SETUP (SCHEDULED) ${NC}"
echo -e "${CYAN}=========================================${NC}"

# =========================
# Detect Python via Windows
# =========================
PYTHON_WIN_PATH=$(where.exe python 2>/dev/null | head -n 1 | tr -d '\r')

if [ -z "$PYTHON_WIN_PATH" ]; then
    echo -e "${RED}Python not found on Windows PATH.${NC}"
    exit 1
fi

PYTHON_EXE=$(echo "$PYTHON_WIN_PATH" | sed 's|\\|/|g' | sed 's|^\([A-Za-z]\):|/\L\1|')

echo -e "${GREEN}Using Python:${NC} $PYTHON_EXE"

# =========================
# Virtual environment
# =========================
VENV_DIR="$BASE_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    "$PYTHON_EXE" -m venv "$VENV_DIR"
else
    echo -e "${GREEN}Virtual environment already exists.${NC}"
fi

# =========================
# Activate venv (Git Bash)
# =========================
source "$VENV_DIR/Scripts/activate" || {
    echo -e "${RED}Failed to activate virtual environment.${NC}"
    exit 1
}

# =========================
# Install dependencies
# =========================
echo -e "${GREEN}Installing dependencies...${NC}"
python -m pip install --upgrade pip -q
python -m pip install \
    selenium \
    pandas \
    g4f \
    langdetect \
    streamlit \
    plotly \
    beautifulsoup4 \
    webdriver-manager \
    selenium-stealth \
    matplotlib \
    seaborn -q

# =========================
# Edge Driver check
# =========================
if [ ! -f "$BASE_DIR/msedgedriver.exe" ]; then
    echo -e "${RED}CRITICAL WARNING:${NC} msedgedriver.exe not found."
fi

# =========================
# Database initialization
# =========================
echo -e "${GREEN}Initializing database...${NC}"

python - <<EOF
from src import database_manager
database_manager.init_db()
print("Database initialized successfully.")
EOF

# =========================
# BOT EXECUTION
# =========================
echo -e "${CYAN}Starting BOT automatically...${NC}"
export PYTHONUNBUFFERED=1
python -u src/bot_v2.py

# =========================
# Cleanup
# =========================
deactivate
exit 0
