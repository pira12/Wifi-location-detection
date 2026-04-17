"""recon/target — airodump locked to one BSSID + channel."""

from __future__ import annotations

from wifipi.module import Module, RunContext
from wifipi.options import OptionSpec


class Target(Module):
    NAME = "recon/target"
    CATEGORY = "recon"
    DESCRIPTION = "Channel-locked capture for one AP. Writes <prefix>-NN.cap."
    OPTIONS = {
        "BSSID": OptionSpec(required=True, description="Target AP BSSID.", kind="bssid"),
        "CHANNEL": OptionSpec(required=True, description="Target AP channel.", kind="int"),
        "OUTPUT_PREFIX": OptionSpec(required=False, default=None,
                                    description="Capture filename prefix (default: loot dir/capture)."),
    }
    REQUIRES_TOOLS = ["airodump-ng"]
    BLOCKING = False
    LOOT_SUBDIR = "scans"

    def build_argv(self, opts: dict) -> list[str]:
        iface = opts.get("MON_IFACE")
        if not iface:
            raise RuntimeError("MON_IFACE not set")
        prefix = opts.get("OUTPUT_PREFIX") or "capture"
        return [
            "airodump-ng",
            "-c", str(opts["CHANNEL"]),
            "--bssid", opts["BSSID"],
            "-w", prefix,
            iface,
        ]
