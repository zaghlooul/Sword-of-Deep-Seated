#!/usr/bin/env bash
# SwordSuite — Installation helper
set -e

BOLD='\033[1m'
CYAN='\033[36m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
RESET='\033[0m'

banner() {
    echo -e "\n${CYAN}${BOLD}"
    echo "  ⚔  SwordSuite — Unified Recon & Exploitation Framework"
    echo "     Dork's Eye · Katana · ParamSpider · SQLMap in one professional GUI"
    echo -e "${RESET}"
}

check_tool() {
    local name="$1"
    if command -v "$name" &>/dev/null; then
        echo -e "  ${GREEN}✓${RESET} $name found at $(command -v "$name")"
    else
        echo -e "  ${YELLOW}✗${RESET} $name not found"
    fi
}

banner

echo -e "${BOLD}[1/3] Installing Python dependencies…${RESET}"
pip3 install -r requirements.txt

echo -e "\n${BOLD}[2/3] Checking tool availability…${RESET}"
check_tool "dorks-eye"
check_tool "katana"
check_tool "paramspider"
check_tool "sqlmap"

echo -e "\n${BOLD}[3/3] Optional — install missing tools:${RESET}"
echo ""
echo "  Dork's Eye:"
echo "    pip install dorks-eye"
echo "    # OR: git clone https://github.com/BullsEye0/dorks-eye && cd dorks-eye && pip install ."
echo ""
echo "  Katana (requires Go ≥ 1.21):"
echo "    go install github.com/projectdiscovery/katana/cmd/katana@latest"
echo "    # OR: apt install katana  (Kali Linux)"
echo ""
echo "  ParamSpider:"
echo "    pip install paramspider"
echo ""
echo "  SQLMap:"
echo "    pip install sqlmap"
echo "    # OR: apt install sqlmap"
echo ""

echo -e "${GREEN}${BOLD}Installation complete!${RESET}"
echo ""
echo -e "  Run: ${CYAN}python3 main.py${RESET}"
echo ""
