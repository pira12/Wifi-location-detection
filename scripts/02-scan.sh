#!/usr/bin/env bash
# General airspace scan. Use this to discover your test AP's BSSID,
# channel, and the MAC of your test client.
# Usage: sudo ./02-scan.sh wlan1mon

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

IFACE="${1:-}"
[[ -z "$IFACE" ]] && die "Usage: $0 <monitor-iface>   (e.g. wlan1mon)"

info "Starting airodump-ng on $IFACE. Ctrl-C to stop."
info "Note your target AP's BSSID, its channel, and the STATION MAC of your test client."
airodump-ng "$IFACE"
