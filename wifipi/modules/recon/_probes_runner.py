"""Probe-request harvester.

Spawns airodump-ng with CSV+pcap output; on SIGTERM (or DURATION
timeout) kills airodump, parses the CSV, and writes summary.txt.
"""

from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path

from wifipi.probes import load_ouis, parse_airodump_csv, render_summary


REPO_ROOT = Path(__file__).resolve().parents[3]
OUI_FILE = REPO_ROOT / "configs" / "oui-short.txt"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--mon-iface", required=True)
    p.add_argument("--channel", type=int, default=None)
    p.add_argument("--duration", type=int, default=0)
    args = p.parse_args()

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    prefix = workdir / "probes"

    argv = ["airodump-ng",
            "--output-format", "csv,pcap",
            "-w", str(prefix),
            args.mon_iface]
    if args.channel:
        argv[1:1] = ["-c", str(args.channel)]

    airodump_log = open(workdir / "airodump.log", "ab")
    airodump = subprocess.Popen(argv, stdout=airodump_log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL)

    running = {"go": True}

    def stop(_sig, _frm):
        running["go"] = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    started = time.time()
    try:
        while running["go"]:
            if args.duration and time.time() - started >= args.duration:
                break
            if airodump.poll() is not None:
                print("[x] airodump-ng exited early", flush=True)
                break
            time.sleep(1)
    finally:
        if airodump.poll() is None:
            airodump.terminate()
            try:
                airodump.wait(timeout=3)
            except subprocess.TimeoutExpired:
                airodump.kill()
        airodump_log.close()

    csv_path = Path(str(prefix) + "-01.csv")
    summary_path = workdir / "summary.txt"
    if csv_path.exists():
        ouis = load_ouis(OUI_FILE) if OUI_FILE.exists() else {}
        records = parse_airodump_csv(csv_path)
        summary_path.write_text(render_summary(records, ouis))
        print(f"[+] summary: {summary_path}", flush=True)
    else:
        print(f"[x] no CSV produced at {csv_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
