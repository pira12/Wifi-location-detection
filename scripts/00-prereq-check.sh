#!/usr/bin/env bash
# Sanity-check the Pi is ready for the demo:
#   - required tools installed
#   - wireless interfaces visible
#   - hint about how to verify monitor mode + injection

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

info "Checking required tools..."
missing=()
for t in airmon-ng airodump-ng aireplay-ng aircrack-ng hostapd dnsmasq iw iptables; do
    if ! command -v "$t" >/dev/null 2>&1; then
        missing+=("$t")
    fi
done

if (( ${#missing[@]} > 0 )); then
    warn "Missing: ${missing[*]}"
    echo "  Install with:"
    echo "    sudo apt install -y kali-tools-wireless dnsmasq hostapd iptables"
else
    info "All required tools present."
fi

info "Wireless interfaces:"
iw dev | awk '$1=="Interface"{print "  - "$2}'

info "USB devices that look like Wi-Fi adapters:"
lsusb | grep -iE 'wi(reless|fi)|802\.11|atheros|realtek|mediatek|ralink' \
    || warn "Nothing obvious in lsusb output. Plug in your USB adapter."

cat <<'EOF'

To verify monitor mode + packet injection on your USB adapter (e.g. wlan1):

    sudo airmon-ng start wlan1
    sudo aireplay-ng --test wlan1mon

You want to see "Injection is working!" in the output.
EOF
