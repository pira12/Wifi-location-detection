"""attack/beacon-flood — flood fake beacon frames via mdk4."""

from __future__ import annotations

from pathlib import Path

from wifipi.module import Module
from wifipi.options import OptionSpec


DEFAULT_LIST = str(
    Path(__file__).resolve().parents[3] / "configs" / "ssidlist-top100.txt"
)


class BeaconFlood(Module):
    NAME = "attack/beacon-flood"
    CATEGORY = "attack"
    DESCRIPTION = "Beacon flood fake SSIDs (mdk4 b) from a wordlist."
    OPTIONS = {
        "SSID_LIST": OptionSpec(required=False, default=DEFAULT_LIST,
                                description="Path to SSID list (one per line).",
                                kind="path"),
        "CHANNEL":   OptionSpec(required=False, default=None,
                                description="Lock to one channel (else hop).",
                                kind="int"),
        "PPS":       OptionSpec(required=False, default="50",
                                description="Packets per second (mdk4 -s).",
                                kind="int"),
    }
    REQUIRES_TOOLS = ["mdk4"]
    BLOCKING = False
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "attacks"

    def build_argv(self, opts: dict) -> list[str]:
        iface = opts.get("MON_IFACE")
        if not iface:
            raise RuntimeError("MON_IFACE not set")
        ssid_list = opts.get("SSID_LIST") or DEFAULT_LIST
        argv = ["mdk4", iface, "b",
                "-f", str(ssid_list),
                "-s", str(opts.get("PPS", "50"))]
        channel = opts.get("CHANNEL")
        if channel:
            argv += ["-c", str(channel)]
        return argv
