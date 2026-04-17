#!/usr/bin/env bash
# Channel-locked capture for one specific AP. Records to <prefix>-NN.cap.
# Run this in its own terminal; it writes the handshake file you need
# for the crack step.
#
# Usage:
#   sudo ./03-target-capture.sh -c 6 -b AA:BB:CC:11:22:33 -i wlan1mon -o capture

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

usage() {
    die "Usage: $0 -c <channel> -b <bssid> -i <iface> [-o <prefix>]"
}

CHANNEL="" BSSID="" IFACE="" OUTPUT="capture"
while getopts "c:b:i:o:" opt; do
    case "$opt" in
        c) CHANNEL=$OPTARG ;;
        b) BSSID=$OPTARG ;;
        i) IFACE=$OPTARG ;;
        o) OUTPUT=$OPTARG ;;
        *) usage ;;
    esac
done

[[ -z "$CHANNEL" || -z "$BSSID" || -z "$IFACE" ]] && usage

warn "About to capture targeted on:"
warn "  BSSID  = $BSSID"
warn "  Channel= $CHANNEL"
warn "  Iface  = $IFACE"
warn "Make sure $BSSID is YOUR OWN AP (check lab-notes/inventory.md)."
warn "Cancel now (Ctrl-C) if it isn't."
sleep 3

info "Capturing — output prefix: $OUTPUT"
airodump-ng -c "$CHANNEL" --bssid "$BSSID" -w "$OUTPUT" "$IFACE"
