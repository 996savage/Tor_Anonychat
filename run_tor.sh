#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
#  SecureChat over Tor Launcher
#  Fully anonymous, no IP exposure, works anywhere
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Colors
RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[1;33m'
CYN='\033[0;36m'
BLU='\033[0;34m'
MAG='\033[0;35m'
DIM='\033[2m'
RST='\033[0m'

clear
echo -e "${CYN}╔════════════════════════════════════════════════════════════════════╗${RST}"
echo -e "${CYN}║${RST}  ${MAG}▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓${CYN}║${RST}"
echo -e "${CYN}║${RST}  ${MAG}▓${RST}                                                              ${MAG}▓${CYN}║${RST}"
echo -e "${CYN}║${RST}  ${MAG}▓${RST}     ${GRN}🔐 SECURECHAT OVER TOR — FULLY ANONYMOUS 🔐${RST}          ${MAG}▓${CYN}║${RST}"
echo -e "${CYN}║${RST}  ${MAG}▓${RST}                                                              ${MAG}▓${CYN}║${RST}"
echo -e "${CYN}║${RST}  ${MAG}▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓${CYN}║${RST}"
echo -e "${CYN}╚════════════════════════════════════════════════════════════════════╝${RST}"
echo ""

# ── Check Tor ─────────────────────────────────────────────────────────────────
check_tor() {
    if ! command -v tor &> /dev/null; then
        echo -e "${YEL}[!] Tor not installed. Installing...${RST}"
        sudo apt update && sudo apt install tor -y
    fi

    if ! systemctl is-active --quiet tor; then
        echo -e "${YEL}[!] Starting Tor service...${RST}"
        sudo systemctl start tor
        sleep 3
    fi

    if systemctl is-active --quiet tor; then
        echo -e "${GRN}[✓] Tor is running${RST}"
    else
        echo -e "${RED}[✗] Tor failed to start. Run: sudo systemctl start tor${RST}"
        exit 1
    fi
}

# ── Check torsocks ────────────────────────────────────────────────────────────
check_torsocks() {
    if ! command -v torsocks &> /dev/null; then
        echo -e "${YEL}[!] Installing torsocks...${RST}"
        sudo apt install torsocks -y
    fi
    echo -e "${GRN}[✓] torsocks available${RST}"
}

# ── Get onion address ─────────────────────────────────────────────────────────
get_onion() {
    # Ensure hidden service directory exists
    sudo mkdir -p /var/lib/tor/securechat/
    sudo chown -R debian-tor:debian-tor /var/lib/tor/securechat/
    
    # Add config to torrc if not present
    if ! grep -q "HiddenServiceDir /var/lib/tor/securechat/" /etc/tor/torrc 2>/dev/null; then
        echo -e "${YEL}[!] Configuring Tor hidden service...${RST}"
        echo "" | sudo tee -a /etc/tor/torrc
        echo "# SecureChat hidden service" | sudo tee -a /etc/tor/torrc
        echo "HiddenServiceDir /var/lib/tor/securechat/" | sudo tee -a /etc/tor/torrc
        echo "HiddenServicePort 57311 127.0.0.1:57311" | sudo tee -a /etc/tor/torrc
        sudo systemctl restart tor
        sleep 5
    fi
    
    ONION=$(sudo cat /var/lib/tor/securechat/hostname 2>/dev/null | tr -d '\n')
    if [ -z "$ONION" ]; then
        echo -e "${RED}[✗] No onion address found. Waiting for Tor...${RST}"
        sleep 5
        ONION=$(sudo cat /var/lib/tor/securechat/hostname 2>/dev/null | tr -d '\n')
        if [ -z "$ONION" ]; then
            echo -e "${RED}[✗] Failed to get onion address. Check Tor configuration.${RST}"
            exit 1
        fi
    fi
    echo "$ONION"
}

# ── Main menu ─────────────────────────────────────────────────────────────────
show_menu() {
    echo ""
    echo "  ${CYN}══════════════════════════════════════════════════${RST}"
    echo "  ${GRN}  Select mode:${RST}"
    echo "  ${CYN}══════════════════════════════════════════════════${RST}"
    echo ""
    echo "    ${BLU}[1]${RST}  ${GRN}Host a session${RST}  ${DIM}(generate onion address, wait for peer)${RST}"
    echo "    ${BLU}[2]${RST}  ${GRN}Connect to session${RST}  ${DIM}(enter onion address from host)${RST}"
    echo "    ${BLU}[3]${RST}  ${GRN}LAN / Direct mode${RST}  ${DIM}(no Tor, same network)${RST}"
    echo "    ${BLU}[4]${RST}  ${RED}Exit${RST}"
    echo ""
}

# ── Host mode (Tor) ──────────────────────────────────────────────────────────
host_mode() {
    clear
    echo -e "${CYN}╔════════════════════════════════════════════════════════════════════╗${RST}"
    echo -e "${CYN}║${RST}                    ${GRN}🔐 HOST MODE (TOR HIDDEN SERVICE)${RST}                    ${CYN}║${RST}"
    echo -e "${CYN}╚════════════════════════════════════════════════════════════════════╝${RST}"
    echo ""
    
    ONION=$(get_onion)
    
    echo -e "${GRN}  ✓ Tor hidden service is ready!${RST}"
    echo ""
    echo -e "${YEL}  ┌─────────────────────────────────────────────────────────────────┐${RST}"
    echo -e "${YEL}  │${RST}                                                                  ${YEL}│${RST}"
    echo -e "${YEL}  │${RST}     ${CYN}Share this address with your peer:${RST}                               ${YEL}│${RST}"
    echo -e "${YEL}  │${RST}                                                                  ${YEL}│${RST}"
    echo -e "${YEL}  │${RST}     ${MAG}${ONION}${RST}  ${YEL}│${RST}"
    echo -e "${YEL}  │${RST}                                                                  ${YEL}│${RST}"
    echo -e "${YEL}  │${RST}     ${DIM}Port: 57311 (Tor handles this automatically)${RST}                    ${YEL}│${RST}"
    echo -e "${YEL}  └─────────────────────────────────────────────────────────────────┘${RST}"
    echo ""
    echo -e "${YEL}  ⏳ Waiting for peer to connect... (timeout: 15 minutes)${RST}"
    echo -e "${DIM}  Press Ctrl+C to cancel${RST}"
    echo ""
    
    # Run SecureChat host through Tor
    torsocks python3 securechat/securechat.py host --port 57311
}

# ── Connect mode (Tor) ───────────────────────────────────────────────────────
connect_mode() {
    clear
    echo -e "${CYN}╔════════════════════════════════════════════════════════════════════╗${RST}"
    echo -e "${CYN}║${RST}                  ${GRN}🔐 CONNECT MODE (VIA TOR HIDDEN SERVICE)${RST}                 ${CYN}║${RST}"
    echo -e "${CYN}╚════════════════════════════════════════════════════════════════════╝${RST}"
    echo ""
    
    echo -e "${YEL}  Enter the onion address from the host:${RST}"
    echo -e "${DIM}  (e.g., abc123xyz456789.onion)${RST}"
    echo ""
    read -p "  ➤ " ONION
    
    if [[ ! "$ONION" =~ \.onion$ ]]; then
        echo -e "${RED}[✗] Invalid onion address. Must end with .onion${RST}"
        sleep 2
        return
    fi
    
    echo ""
    echo -e "${YEL}  ⏳ Connecting through Tor to ${ONION}...${RST}"
    echo ""
    
    # Run SecureChat connect through Tor
    # We need to pass the onion address to the connect function
    torsocks python3 -c "
import sys
sys.path.insert(0, 'securechat')
from securechat.securechat import run_connect
run_connect(port=57311)
" 
    # Note: The user will be prompted for IP - enter the onion address
}

# ── LAN mode (original) ───────────────────────────────────────────────────────
lan_mode() {
    clear
    echo -e "${CYN}╔════════════════════════════════════════════════════════════════════╗${RST}"
    echo -e "${CYN}║${RST}                     ${GRN}🌐 LAN / DIRECT CONNECT MODE${RST}                        ${CYN}║${RST}"
    echo -e "${CYN}╚════════════════════════════════════════════════════════════════════╝${RST}"
    echo ""
    echo "  [1]  Host (wait for connection)"
    echo "  [2]  Connect (enter IP address)"
    echo "  [3]  Back"
    echo ""
    read -p "  Choice: " lan_choice
    
    case $lan_choice in
        1)
            python3 securechat/securechat.py host
            ;;
        2)
            python3 securechat/securechat.py connect
            ;;
        *)
            return
            ;;
    esac
}

# ── Main entry point ─────────────────────────────────────────────────────────
main() {
    check_tor
    check_torsocks
    
    while true; do
        show_menu
        read -p "  Choice [1/2/3/4]: " choice
        
        case $choice in
            1)
                host_mode
                ;;
            2)
                connect_mode
                ;;
            3)
                lan_mode
                ;;
            4)
                clear
                echo -e "${GRN}  SecureChat closed. No logs. No history. No trace.${RST}"
                exit 0
                ;;
            *)
                echo -e "${RED}  Invalid choice${RST}"
                ;;
        esac
    done
}

main