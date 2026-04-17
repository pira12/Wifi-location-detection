#!/usr/bin/env bash
# Tear down everything the demo set up:
#   - kill hostapd / dnsmasq processes for this project
#   - flush the iptables rules we added
#   - disable IP forwarding
#   - take any monitor-mode interfaces down
#   - restart NetworkManager so normal Wi-Fi works again

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

info "Stopping hostapd and dnsmasq..."
pkill -f "hostapd .*hostapd-rogue\.conf" || true
pkill -f "dnsmasq .*dnsmasq-rogue\.conf"  || true

info "Flushing iptables NAT and FORWARD chains..."
iptables -t nat -F POSTROUTING
iptables -F FORWARD

info "Disabling IP forwarding..."
sysctl -w net.ipv4.ip_forward=0 >/dev/null

info "Stopping monitor-mode interfaces..."
for iface in $(iw dev | awk '$1=="Interface"{print $2}'); do
    if iw dev "$iface" info 2>/dev/null | grep -q 'type monitor'; then
        airmon-ng stop "$iface" || true
    fi
done

info "Restarting NetworkManager..."
systemctl restart NetworkManager 2>/dev/null \
    || systemctl restart wpa_supplicant 2>/dev/null \
    || warn "Couldn't restart a network service. Reconnect Wi-Fi manually."

info "Done."
