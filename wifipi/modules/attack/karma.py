"""attack/karma — hostapd-mana rogue AP answering any probe request."""

from __future__ import annotations

from wifipi.module import Module
from wifipi.options import OptionSpec


class Karma(Module):
    NAME = "attack/karma"
    CATEGORY = "attack"
    DESCRIPTION = "Rogue AP that answers every probe request (hostapd-mana enable_karma=1)."
    OPTIONS = {
        "CHANNEL":        OptionSpec(required=False, default="6",
                                     description="AP channel.", kind="int"),
        "UPSTREAM_IFACE": OptionSpec(required=False, default="eth0",
                                     description="NAT egress interface."),
    }
    REQUIRES_TOOLS = ["hostapd-mana", "dnsmasq", "iptables", "tcpdump"]
    BLOCKING = False
    REQUIRES_CONFIRMATION = True
    LOOT_SUBDIR = "attacks"

    def build_argv(self, opts: dict) -> list[str]:
        ap = opts.get("AP_IFACE")
        if not ap:
            raise RuntimeError("AP_IFACE not set — need a rogue-AP adapter")
        return [
            "python3", "-m", "wifipi.modules.attack._karma_runner",
            "--workdir", opts.get("_WORKDIR", "/tmp/karma"),
            "--ap-iface", ap,
            "--channel", str(opts.get("CHANNEL", "6")),
            "--upstream", opts.get("UPSTREAM_IFACE", "eth0"),
        ]
