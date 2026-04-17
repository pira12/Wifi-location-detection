#!/usr/bin/env bash
# Put one or more wireless interfaces into monitor mode.
#
# Usage:
#   sudo ./01-monitor-up.sh wlan1                # single adapter
#   sudo ./01-monitor-up.sh wlan1 wlan2          # both USB adapters

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

(( $# > 0 )) || die "Usage: $0 <iface> [<iface> ...]   (e.g. wlan1 wlan2)"

info "Killing processes that interfere with monitor mode..."
airmon-ng check kill

for IFACE in "$@"; do
    info "Putting $IFACE into monitor mode..."
    airmon-ng start "$IFACE"
done

info "Current wireless interfaces:"
iw dev
