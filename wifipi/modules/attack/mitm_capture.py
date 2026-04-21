"""attack/mitm-capture — tcpdump on AP_IFACE for MITM packet capture.

Assumes a rogue AP module (evil-twin, karma, captive-portal, dns-spoof)
is already running on AP_IFACE.
"""

from __future__ import annotations

from wifipi.module import Module
from wifipi.options import OptionSpec


class MitmCapture(Module):
    NAME = "attack/mitm-capture"
    CATEGORY = "attack"
    DESCRIPTION = "Standalone tcpdump pcap on AP_IFACE (pair with any rogue AP module)."
    OPTIONS = {
        "FILTER":        OptionSpec(required=False, default=None,
                                    description="BPF expression (e.g. 'port 53')."),
        "SNAPLEN":       OptionSpec(required=False, default="0",
                                    description="tcpdump -s (0 = full).", kind="int"),
        "OUTPUT_PREFIX": OptionSpec(required=False, default=None,
                                    description="Output .pcap prefix (default: loot dir/capture)."),
    }
    REQUIRES_TOOLS = ["tcpdump"]
    BLOCKING = False
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "attacks"

    def build_argv(self, opts: dict) -> list[str]:
        iface = opts.get("AP_IFACE")
        if not iface:
            raise RuntimeError("AP_IFACE not set (need a rogue-AP adapter)")
        prefix = opts.get("OUTPUT_PREFIX") or "capture"
        argv = ["tcpdump",
                "-i", iface,
                "-n",
                "-s", str(opts.get("SNAPLEN", "0")),
                "-w", f"{prefix}-01.pcap"]
        flt = opts.get("FILTER")
        if flt:
            argv.append(flt)
        return argv
