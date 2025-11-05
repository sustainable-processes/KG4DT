#!/usr/bin/env bash
# docker_macos_doctor.sh
# Purpose: Help diagnose and mitigate Docker Desktop startup issues on macOS,
# specifically: "com.docker.virtualization: process terminated unexpectedly: use of closed network connection".
#
# Non-destructive by default. It prints findings and safe actions.
# Use flags to opt in to more aggressive steps.
#
# Usage:
#   bash scripts/macos/docker_macos_doctor.sh [--kill-ports] [--show-logs] [--print-reset]
#
# Flags:
#   --kill-ports   Attempt to kill processes occupying ports 5000 and 7200 (uses lsof + kill -9).
#   --show-logs    Show tail of Docker Desktop logs if available.
#   --print-reset  Print step-by-step reset commands for Docker Desktop networking and VM (does NOT execute).
#
# Notes:
# - For destructive resets (factory reset, deleting VM files), follow printed instructions manually.
# - Always fully quit Docker Desktop (from menu bar) before running reset steps.

set -euo pipefail

RED="\033[31m"; GREEN="\033[32m"; YELLOW="\033[33m"; BLUE="\033[34m"; NC="\033[0m"

KILL_PORTS=false
SHOW_LOGS=false
PRINT_RESET=false

for arg in "$@"; do
  case "$arg" in
    --kill-ports) KILL_PORTS=true ;;
    --show-logs)  SHOW_LOGS=true ;;
    --print-reset) PRINT_RESET=true ;;
    *) echo -e "${YELLOW}Unknown option:${NC} $arg" ;;
  esac
done

header() { echo -e "\n${BLUE}==> $*${NC}"; }
info()   { echo -e "${GREEN}[info]${NC} $*"; }
warn()   { echo -e "${YELLOW}[warn]${NC} $*"; }
error()  { echo -e "${RED}[error]${NC} $*"; }

header "Environment"
uname -a || true
sw_vers 2>/dev/null || true

header "Checking for VPNs / Network Filters (known to break vpnkit)"
# This is heuristic; instruct the user rather than trying to disable
if /usr/bin/pgrep -f -q "(Lulu|LuLu)"; then warn "LuLu firewall appears to be running"; fi
if /usr/bin/pgrep -f -q "Little Snitch"; then warn "Little Snitch appears to be running"; fi
if /usr/bin/pgrep -f -q "openvpn|wireguard|tailscale|zerotier|zscaler|globalprotect"; then warn "A VPN/Network extension appears to be active"; fi
info "If Docker still fails, temporarily disable VPNs and Network Filters in System Settings → Network."

header "Port checks (5000, 7200)"
for p in 5000 7200; do
  if lsof -i :"$p" -n -P 2>/dev/null | tail -n +2 | awk '{print $2}' | grep -q .; then
    warn "Port $p is in use:"
    lsof -i :"$p" -n -P | sed -n '1,5p'
    if [ "$KILL_PORTS" = true ]; then
      PIDS=$(lsof -i :"$p" -n -P | awk 'NR>1{print $2}' | sort -u)
      warn "Killing PIDs on port $p: $PIDS"
      for pid in $PIDS; do kill -9 "$pid" 2>/dev/null || true; done
      info "Port $p should now be free."
    else
      info "Re-run with --kill-ports to free this port automatically."
    fi
  else
    info "Port $p is free."
  fi
done

header "Docker Desktop process status"
if /usr/bin/pgrep -f -q "com.docker.backend"; then info "Docker backend appears to be running"; else warn "Docker backend not detected"; fi
if /usr/bin/pgrep -f -q "vpnkit"; then info "vpnkit appears to be running"; else warn "vpnkit not detected (it starts with Docker)"; fi

if [ "$SHOW_LOGS" = true ]; then
  header "Recent Docker Desktop logs"
  LOGDIR="$HOME/Library/Containers/com.docker.docker/Data/log"
  if [ -d "$LOGDIR" ]; then
    for f in docker.log vpnkit.log com.docker.backend.log; do
      if [ -f "$LOGDIR/$f" ]; then
        echo "--- $f (last 100 lines) ---"
        tail -n 100 "$LOGDIR/$f" || true
      fi
    done
  else
    warn "Log directory not found: $LOGDIR"
  fi
fi

if [ "$PRINT_RESET" = true ]; then
  header "Reset instructions (manual)"
  cat <<'INSTR'
1) Fully quit Docker Desktop from the menu bar (whale icon → Quit Docker Desktop).
2) Optional safe cleanup (non-destructive):
   - Remove stale Docker API socket:
       rm -f ~/Library/Containers/com.docker.docker/Data/docker-api.sock
3) More aggressive reset (will reset the internal VM; images/containers will be lost):
   - Remove internal VM files:
       rm -rf ~/Library/Containers/com.docker.docker/Data/vms/0
   - Optionally clear networking state (Docker Desktop → Troubleshoot → Reset to factory defaults).
4) Relaunch Docker Desktop and wait for "Docker Engine is running".
5) If on Apple Silicon and you use x86 images, ensure Rosetta is installed:
       softwareupdate --install-rosetta --agree-to-license
6) If issues persist, temporarily disable Network Filters and VPNs:
   - System Settings → Network → Filters / VPN & Extensions → disable or remove rules for Docker while testing.
7) Collect diagnostics for support:
   - Docker Desktop → Troubleshoot → Get Support → Create diagnostics bundle.
   - Or view logs at: ~/Library/Containers/com.docker.docker/Data/log/
INSTR
fi

header "Summary"
info "If Docker Desktop still shows: 'use of closed network connection', it is commonly caused by network extensions interfering with vpnkit or a corrupted internal VM."
info "Use --print-reset to display the exact reset commands."
info "See docs/TROUBLESHOOTING_DOCKER.md (macOS section) for more details."
