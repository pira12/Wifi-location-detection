"""util/prereq-check — verify required tools + enumerate wireless adapters."""

from __future__ import annotations

from wifipi.module import Module, RunContext
from wifipi.options import OptionSpec
from wifipi.procutil import missing_tools, run as run_proc


TOOLS = ["airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng",
         "hostapd", "dnsmasq", "iw", "iptables", "tcpdump"]


class PrereqCheck(Module):
    NAME = "util/prereq-check"
    CATEGORY = "util"
    DESCRIPTION = "Verify required tools and list wireless interfaces."
    OPTIONS: dict[str, OptionSpec] = {}
    REQUIRES_TOOLS: list[str] = []
    BLOCKING = True
    LOOT_SUBDIR = None

    def run(self, ctx: RunContext) -> int:
        missing = missing_tools(TOOLS)
        log_lines: list[str] = []

        if missing:
            log_lines.append(f"MISSING: {', '.join(missing)}")
            log_lines.append("Install: apt install -y aircrack-ng hostapd dnsmasq iptables tcpdump iw")
        else:
            log_lines.append("All required tools present.")

        iw = run_proc(["iw", "dev"], capture_output=True, text=True)
        log_lines.append("--- iw dev ---")
        log_lines.append(iw.stdout.strip() or "(no output)")

        lsusb = run_proc(["lsusb"], capture_output=True, text=True)
        log_lines.append("--- lsusb (wifi-ish entries) ---")
        for line in lsusb.stdout.splitlines():
            low = line.lower()
            if any(k in low for k in ("wireless", "wifi", "wi-fi", "802.11",
                                      "atheros", "realtek", "ralink", "mediatek")):
                log_lines.append(line)

        report = "\n".join(log_lines)
        ctx.log_path.write_text(report)
        print(report)
        print()
        print(f"Report saved: {ctx.log_path}")
        return 0 if not missing else 2
