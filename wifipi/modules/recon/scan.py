"""recon/scan — channel-hopping airodump on MON_IFACE."""

from __future__ import annotations

from wifipi.ifaces import Role
from wifipi.module import Module
from wifipi.options import OptionSpec


class Scan(Module):
    NAME = "recon/scan"
    CATEGORY = "recon"
    DESCRIPTION = "airodump-ng channel-hop scan on MON_IFACE."
    OPTIONS = {
        "CHANNEL": OptionSpec(required=False, default=None,
                              description="Lock scan to one channel (else hop)."),
    }
    REQUIRES_TOOLS = ["airodump-ng"]
    BLOCKING = False
    LOOT_SUBDIR = "scans"

    def build_argv(self, opts: dict) -> list[str]:
        iface = opts.get("MON_IFACE")
        if not iface:
            raise RuntimeError("MON_IFACE not set (run `iface auto` or `iface set mon ...`)")
        argv = ["airodump-ng"]
        channel = opts.get("CHANNEL")
        if channel:
            argv += ["-c", str(channel)]
        argv.append(iface)
        return argv
