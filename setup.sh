#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
#  J.A.R.V.I.S. — Setup Script
#  Installs all dependencies and validates the environment.
# ══════════════════════════════════════════════════════════════════════

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo "   ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗"
echo "   ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝"
echo "   ██║███████║██████╔╝██║   ██║██║███████╗"
echo "   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║"
echo "   █████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║"
echo "   ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝"
echo -e "${NC}"
echo -e "${CYAN}  Setup Script${NC}"
echo ""

# ── System Dependencies ──
echo -e "${YELLOW}[1/4] Checking system dependencies...${NC}"

if command -v apt-get &>/dev/null; then
    echo "  Installing system packages (may require sudo)..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq portaudio19-dev python3-pyaudio python3-dev ffmpeg 2>/dev/null || {
        echo -e "${YELLOW}  Warning: Could not install some system packages.${NC}"
        echo "  Microphone support may be limited without portaudio19-dev."
    }
elif command -v brew &>/dev/null; then
    echo "  Installing system packages via Homebrew..."
    brew install portaudio ffmpeg 2>/dev/null || true
else
    echo -e "${YELLOW}  Warning: Package manager not detected.${NC}"
    echo "  Please install portaudio manually for microphone support."
fi

# ── Python Virtual Environment ──
echo ""
echo -e "${YELLOW}[2/4] Setting up Python virtual environment...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "  Created virtual environment at ${VENV_DIR}"
else
    echo "  Virtual environment already exists."
fi

source "${VENV_DIR}/bin/activate"

# ── Python Dependencies ──
echo ""
echo -e "${YELLOW}[3/4] Installing Python dependencies...${NC}"

pip install --upgrade pip -q
pip install -r "${SCRIPT_DIR}/requirements.txt" -q

echo -e "${GREEN}  All dependencies installed.${NC}"

# ── Environment Check ──
echo ""
echo -e "${YELLOW}[4/4] Checking environment...${NC}"

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${YELLOW}  ⚠  ANTHROPIC_API_KEY is not set.${NC}"
    echo "     Jarvis will run in offline mode with limited capabilities."
    echo "     Set it with: export ANTHROPIC_API_KEY=your-key-here"
else
    echo -e "${GREEN}  ✓ ANTHROPIC_API_KEY is configured.${NC}"
fi

# Check microphone
python3 -c "import pyaudio; p = pyaudio.PyAudio(); p.terminate()" 2>/dev/null && {
    echo -e "${GREEN}  ✓ Microphone support available (PyAudio).${NC}"
} || {
    echo -e "${YELLOW}  ⚠  PyAudio not working — voice input will be disabled.${NC}"
    echo "     You can still use text input mode: python -m jarvis --text"
}

# Check TTS
python3 -c "import edge_tts" 2>/dev/null && {
    echo -e "${GREEN}  ✓ Edge-TTS available (high-quality voice).${NC}"
} || {
    python3 -c "import pyttsx3" 2>/dev/null && {
        echo -e "${YELLOW}  ⚠  Edge-TTS not available, using pyttsx3 fallback.${NC}"
    } || {
        echo -e "${YELLOW}  ⚠  No TTS engine available — voice output will be disabled.${NC}"
    }
}

echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup complete! Launch Jarvis with:${NC}"
echo ""
echo -e "    source venv/bin/activate"
echo -e "    python -m jarvis              ${CYAN}# Auto-detect mode${NC}"
echo -e "    python -m jarvis --text       ${CYAN}# Text input only${NC}"
echo -e "    python -m jarvis --no-voice   ${CYAN}# No spoken output${NC}"
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════${NC}"
