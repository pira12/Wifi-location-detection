"""Entry point invoked via `python3 -m wifipi` or the `wifipi.sh` shell wrapper."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from cmd2 import ansi

from .console import WifipiApp
from .procutil import missing_tools

REQUIRED_TOOLS = [
    "airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng",
    "hostapd", "dnsmasq", "iw", "iptables", "tcpdump",
]

WIFI = r"""
 ██╗    ██╗██╗███████╗██╗
 ██║    ██║██║██╔════╝██║
 ██║ █╗ ██║██║█████╗  ██║
 ██║███╗██║██║██╔══╝  ██║
 ╚███╔███╔╝██║██║     ██║
  ╚══╝╚══╝ ╚═╝╚═╝     ╚═╝
""".strip("\n")

PI_ART = r"""
    .~~.   .~~.
   '. \ ' ' / .'
    .~ .~~~..~.
   : .~.'~'.~. :
  ~ (   ) (   ) ~
 ( : '~'.~.'~' : )
  ~ .~ (   ) ~.
   ~  (  : '~' :  )
    '~ .~~~. ~'
         '~'
     Raspberry Pi
""".strip("\n")


def render_art() -> str:
    """WIFI block art side-by-side with the raspberry, vertically centred."""
    wifi_lines = WIFI.splitlines()
    pi_lines = PI_ART.splitlines()
    diff = len(pi_lines) - len(wifi_lines)
    pad_top = max(0, diff // 2)
    pad_bot = max(0, diff - pad_top)
    wifi_lines = [""] * pad_top + wifi_lines + [""] * pad_bot
    width = max((len(l) for l in wifi_lines), default=0)
    out = []
    for w, p in zip(wifi_lines, pi_lines):
        left = ansi.style(w.ljust(width), fg=ansi.Fg.CYAN, bold=True)
        right = ansi.style(p, fg=ansi.Fg.CYAN, bold=True)
        out.append(f"{left}   {right}")
    return "\n".join(out)

BANNER = r"""
 ╔════════════════════════════════════════════════════════════════╗
 ║ wifipi — WiFi Pineapple Equivalent on Raspberry Pi             ║
 ║ Authorised lab use only. Targets must be YOUR devices          ║
 ║ (see lab-notes/inventory.md). Dutch / EU law applies.           ║
 ╚════════════════════════════════════════════════════════════════╝
"""


def main() -> int:
    if os.geteuid() != 0:
        print(ansi.style("[x] wifipi must run as root (sudo ./wifipi.sh).", fg=ansi.Fg.RED), file=sys.stderr)
        return 1

    repo_root = Path(__file__).resolve().parent.parent
    print(render_art())
    print(ansi.style(BANNER, fg=ansi.Fg.RED))
    try:
        input("Press Enter to acknowledge and continue... ")
    except EOFError:
        return 0

    missing = missing_tools(REQUIRED_TOOLS)
    if missing:
        print(ansi.style(
            f"[!] missing system tools: {', '.join(missing)}",
            fg=ansi.Fg.YELLOW,
        ), file=sys.stderr)
        print(ansi.style(
            "    install with: sudo apt install -y aircrack-ng hostapd "
            "dnsmasq iptables tcpdump iw",
            fg=ansi.Fg.YELLOW,
        ), file=sys.stderr)
        print(ansi.style(
            "    modules that need these tools will refuse to load until installed.",
            fg=ansi.Fg.YELLOW,
        ), file=sys.stderr)

    app = WifipiApp(repo_root=repo_root)
    print(f"[*] loaded {len(app._modules)} modules; "
          f"inventory: {len(app.inventory.bssids)} BSSIDs, {len(app.inventory.clients)} clients")
    print(ansi.style(
        "[*] tip: prefix any shell command with `!` (e.g. `!ls loot/`, `!cat loot/…/run.log`)",
        fg=ansi.Fg.CYAN,
    ))
    return app.cmdloop()


if __name__ == "__main__":
    sys.exit(main() or 0)
