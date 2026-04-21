"""attack/ssid-pool — broadcast SSIDs harvested from a probes CSV."""

from __future__ import annotations

from wifipi.module import Module
from wifipi.options import OptionSpec


class SsidPool(Module):
    NAME = "attack/ssid-pool"
    CATEGORY = "attack"
    DESCRIPTION = "hostapd-mana responder seeded with SSIDs harvested from recon/probes."
    OPTIONS = {
        "PROBES_CSV":     OptionSpec(required=True,
                                     description="Path to airodump -01.csv from recon/probes.",
                                     kind="path"),
        "CHANNEL":        OptionSpec(required=False, default="6",
                                     description="AP channel.", kind="int"),
        "UPSTREAM_IFACE": OptionSpec(required=False, default="eth0",
                                     description="NAT egress interface."),
        "MAX_SSIDS":      OptionSpec(required=False, default="50",
                                     description="Cap on SSID pool size.",
                                     kind="int"),
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
            "python3", "-m", "wifipi.modules.attack._ssid_pool_runner",
            "--workdir", opts.get("_WORKDIR", "/tmp/ssid-pool"),
            "--ap-iface", ap,
            "--probes-csv", opts["PROBES_CSV"],
            "--channel", str(opts.get("CHANNEL", "6")),
            "--upstream", opts.get("UPSTREAM_IFACE", "eth0"),
            "--max-ssids", str(opts.get("MAX_SSIDS", "50")),
        ]
