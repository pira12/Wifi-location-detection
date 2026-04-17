#!/usr/bin/env bash
# Put a wireless interface into monitor mode.
# Usage: sudo ./01-monitor-up.sh wlan1

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

IFACE="${1:-}"
[[ -z "$IFACE" ]] && die "Usage: $0 <iface>   (e.g. wlan1)"

info "Killing processes that interfere with monitor mode..."
airmon-ng check kill

info "Putting $IFACE into monitor mode..."
airmon-ng start "$IFACE"

info "Current wireless interfaces:"
iw dev
